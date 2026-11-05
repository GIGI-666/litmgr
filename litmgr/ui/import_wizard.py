"""导入向导。

【作用】分步骤把论文卡片 txt / PDF / 翻译 md / 附件导入系统：
    第 1 步 选择文件或文件夹（可多次添加；文件夹会递归）
    第 2 步 预览自动配对结果（每篇论文对应哪些文件；重复论文默认跳过；可取消勾选）
    第 3 步 处理未识别的标签（卡片里有、字段里没有的内容）：暂存 / 并入上一字段 /
            映射到已有字段（并记住为别名）/ 新建字段 / 忽略
    第 4 步 显示导入结果
【依赖】services.import_service（通过 AppContext）；importers.file_pairing（仅用于类型）。
【被谁调用】ui.window_manager.open_import_wizard（主窗口“导入”按钮）。
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (QComboBox, QDialog, QFileDialog, QHBoxLayout, QLabel, QListWidget,
                               QPushButton, QStackedWidget, QTableWidget, QTableWidgetItem,
                               QTextBrowser, QVBoxLayout, QWidget)

from ..core.field_types import FIELD_TYPES
from ..services.app_context import AppContext
from ..services.import_service import (ACT_FIELD, ACT_IGNORE, ACT_MERGE, ACT_NEW, ACT_PENDING,
                                       ImportPlan, LabelDecision)
from .utils import guarded

ACTIONS = [(ACT_PENDING, "暂存到“待归类内容”"), (ACT_MERGE, "并入上一个字段的内容"),
           (ACT_FIELD, "映射到已有字段（并记住）"), (ACT_NEW, "新建字段"), (ACT_IGNORE, "忽略")]


class ImportWizard(QDialog):
    def __init__(self, parent, ctx: AppContext) -> None:
        super().__init__(parent)
        self.ctx = ctx
        self.paths: list[Path] = []
        self.plan: ImportPlan | None = None
        self.setWindowTitle("导入论文")
        self.resize(1000, 640)

        lay = QVBoxLayout(self)
        self.stack = QStackedWidget()
        lay.addWidget(self.stack, 1)
        self._build_pick_page()
        self._build_preview_page()
        self._build_labels_page()
        self._build_result_page()

        nav = QHBoxLayout()
        self.back_btn = QPushButton("上一步")
        self.next_btn = QPushButton("下一步")
        self.cancel_btn = QPushButton("取消")
        self.back_btn.clicked.connect(self._back)
        self.next_btn.clicked.connect(self._next)
        self.cancel_btn.clicked.connect(self.reject)
        nav.addStretch(1)
        for b in (self.cancel_btn, self.back_btn, self.next_btn):
            nav.addWidget(b)
        lay.addLayout(nav)
        self._update_nav()

    # ---------- 第 1 页：选择 ----------
    def _build_pick_page(self) -> None:
        page = QWidget()
        v = QVBoxLayout(page)
        v.addWidget(QLabel(
            "<b>选择要导入的文件或文件夹</b><br>"
            "可一次选整个文件夹（含卡片、PDF、翻译、补充材料等），系统会按文件名自动配对：<br>"
            "<code>标题2406论文卡片.txt</code> / <code>标题2406.pdf</code> / "
            "<code>标题2406补充材料.pdf</code> / <code>标题2406翻译.md</code>"))
        row = QHBoxLayout()
        b1, b2, b3 = QPushButton("添加文件夹…"), QPushButton("添加文件…"), QPushButton("清空")
        b1.clicked.connect(self._add_folder)
        b2.clicked.connect(self._add_files)
        b3.clicked.connect(self._clear_paths)
        for b in (b1, b2, b3):
            row.addWidget(b)
        row.addStretch(1)
        v.addLayout(row)
        self.path_list = QListWidget()
        v.addWidget(self.path_list, 1)
        crow = QHBoxLayout()
        crow.addWidget(QLabel("导入后加入分组："))
        self.collection_box = QComboBox()
        self.collection_box.addItem("（不加入分组）", None)
        for c in self.ctx.organize.collections():
            self.collection_box.addItem(c.name, c.id)
        crow.addWidget(self.collection_box)
        crow.addStretch(1)
        v.addLayout(crow)
        self.stack.addWidget(page)

    def _add_folder(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if d:
            self._add_path(Path(d))

    def _add_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "选择文件")
        for f in files:
            self._add_path(Path(f))

    def _add_path(self, p: Path) -> None:
        if p not in self.paths:
            self.paths.append(p)
            self.path_list.addItem(str(p))
        self._update_nav()

    def _clear_paths(self) -> None:
        self.paths.clear()
        self.path_list.clear()
        self._update_nav()

    # ---------- 第 2 页：预览 ----------
    def _build_preview_page(self) -> None:
        page = QWidget()
        v = QVBoxLayout(page)
        self.preview_hint = QLabel()
        v.addWidget(self.preview_hint)
        self.preview = QTableWidget(0, 7)
        self.preview.setHorizontalHeaderLabels(["导入", "标题", "卡片", "PDF", "翻译", "附件", "提示"])
        self.preview.verticalHeader().setVisible(False)
        self.preview.setColumnWidth(0, 50)
        self.preview.setColumnWidth(1, 380)
        for c in (2, 3, 4, 5):
            self.preview.setColumnWidth(c, 55)
        self.preview.horizontalHeader().setStretchLastSection(True)
        self.preview.itemChanged.connect(self._on_preview_check)
        v.addWidget(self.preview, 1)
        self.stack.addWidget(page)

    def _fill_preview(self) -> None:
        self.preview.blockSignals(True)
        self.preview.setRowCount(len(self.plan.items))
        for r, it in enumerate(self.plan.items):
            g = it.group
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            chk.setCheckState(Qt.Checked if it.action == "import" else Qt.Unchecked)
            vals = [it.title, "✓" if g.card else "—", str(len(g.pdfs)), "✓" if g.translations else "—",
                    str(len(g.attachments)), "；".join(it.warnings)]
            self.preview.setItem(r, 0, chk)
            for c, text in enumerate(vals, start=1):
                cell = QTableWidgetItem(text)
                cell.setFlags(Qt.ItemIsEnabled)
                cell.setToolTip(text)
                self.preview.setItem(r, c, cell)
        self.preview.blockSignals(False)
        n_imp = sum(1 for i in self.plan.items if i.action == "import")
        self.preview_hint.setText(
            f"共识别 <b>{len(self.plan.items)}</b> 篇论文，将导入 <b>{n_imp}</b> 篇。"
            "取消勾选即跳过该篇。")

    def _on_preview_check(self, item: QTableWidgetItem) -> None:
        if item.column() == 0 and self.plan:
            self.plan.items[item.row()].action = "import" if item.checkState() == Qt.Checked else "skip"
            n = sum(1 for i in self.plan.items if i.action == "import")
            self.preview_hint.setText(f"共识别 <b>{len(self.plan.items)}</b> 篇论文，将导入 <b>{n}</b> 篇。"
                                      "取消勾选即跳过该篇。")

    # ---------- 第 3 页：未知标签 ----------
    def _build_labels_page(self) -> None:
        page = QWidget()
        v = QVBoxLayout(page)
        self.labels_hint = QLabel()
        self.labels_hint.setWordWrap(True)
        v.addWidget(self.labels_hint)
        self.labels = QTableWidget(0, 5)
        self.labels.setHorizontalHeaderLabels(["卡片里的标签", "出现次数", "内容示例", "处理方式", "目标"])
        self.labels.verticalHeader().setVisible(False)
        self.labels.setColumnWidth(0, 170)
        self.labels.setColumnWidth(1, 70)
        self.labels.setColumnWidth(2, 260)
        self.labels.setColumnWidth(3, 210)
        self.labels.horizontalHeader().setStretchLastSection(True)
        v.addWidget(self.labels, 1)
        self.stack.addWidget(page)

    def _fill_labels(self) -> None:
        fields = self.ctx.fields.list()
        self.labels.setRowCount(len(self.plan.unknown))
        for r, u in enumerate(self.plan.unknown):
            for c, text in enumerate([u.label + ("  (编号)" if u.numbered else ""), str(u.count),
                                      " | ".join(u.samples)]):
                cell = QTableWidgetItem(text)
                cell.setFlags(Qt.ItemIsEnabled)
                cell.setToolTip(text)
                self.labels.setItem(r, c, cell)
            act = QComboBox()
            for key, label in ACTIONS:
                act.addItem(label, key)
            act.setCurrentIndex(max(act.findData(u.default_decision().action), 0))
            target = QComboBox()
            act.currentIndexChanged.connect(lambda _i, a=act, t=target: self._fill_target(a, t, fields))
            self._fill_target(act, target, fields)
            self.labels.setCellWidget(r, 3, act)
            self.labels.setCellWidget(r, 4, target)
        self.labels_hint.setText(
            f"有 <b>{len(self.plan.unknown)}</b> 个标签不在现有字段里。请决定怎么处理——"
            "选“映射/新建”后，下次导入同样写法会自动识别。" if self.plan.unknown
            else "所有标签都已识别，无需处理。")

    @staticmethod
    def _fill_target(act: QComboBox, target: QComboBox, fields) -> None:
        target.clear()
        key = act.currentData()
        if key == ACT_FIELD:
            for f in fields:
                target.addItem(f.name, f.id)
            target.setEnabled(True)
        elif key == ACT_NEW:
            for t in FIELD_TYPES.values():
                target.addItem(f"新字段类型：{t.label}", t.name)
            target.setCurrentIndex(max(target.findData("longtext"), 0))
            target.setEnabled(True)
        else:
            target.setEnabled(False)

    def _collect_decisions(self) -> dict[str, LabelDecision]:
        out: dict[str, LabelDecision] = {}
        for r, u in enumerate(self.plan.unknown):
            act = self.labels.cellWidget(r, 3).currentData()
            tgt = self.labels.cellWidget(r, 4).currentData()
            d = LabelDecision(act)
            if act == ACT_FIELD:
                d.field_id = tgt
            elif act == ACT_NEW:
                d.new_type = tgt or "longtext"
            out[u.key] = d
        return out

    # ---------- 第 4 页：结果 ----------
    def _build_result_page(self) -> None:
        page = QWidget()
        v = QVBoxLayout(page)
        self.result = QTextBrowser()
        v.addWidget(self.result)
        self.stack.addWidget(page)

    # ---------- 导航 ----------
    def _update_nav(self) -> None:
        i = self.stack.currentIndex()
        self.back_btn.setVisible(0 < i < 3)
        self.cancel_btn.setVisible(i < 3)
        self.next_btn.setText({0: "下一步：预览", 1: "下一步", 2: "开始导入", 3: "完成"}[i])
        self.next_btn.setEnabled(bool(self.paths) if i == 0 else True)

    def _back(self) -> None:
        i = self.stack.currentIndex()
        self.stack.setCurrentIndex(max(0, i - 1))
        self._update_nav()

    @guarded
    def _next(self) -> None:
        i = self.stack.currentIndex()
        if i == 0:
            QGuiApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                self.plan = self.ctx.imports.build_plan(self.paths)
            finally:
                QGuiApplication.restoreOverrideCursor()
            self._fill_preview()
            self.stack.setCurrentIndex(1)
        elif i == 1:
            self._fill_labels()
            self.stack.setCurrentIndex(2)
        elif i == 2:
            QGuiApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                res = self.ctx.imports.execute(self.plan, self._collect_decisions(),
                                               self.collection_box.currentData())
            finally:
                QGuiApplication.restoreOverrideCursor()
            lines = [f"<h3>导入完成</h3><p>成功导入 <b>{len(res.created)}</b> 篇，"
                     f"跳过 <b>{res.skipped}</b> 篇。</p>"]
            if res.errors:
                lines.append("<p style='color:#c00'>以下论文导入出错：</p><ul>" +
                             "".join(f"<li>{e}</li>" for e in res.errors) + "</ul>")
            pend = self.ctx.imports.list_pending()
            if pend:
                lines.append(f"<p>仍有 <b>{len(pend)}</b> 条“待归类内容”，"
                             "可在对应论文详情页的“字段”页顶部处理。</p>")
            self.result.setHtml("".join(lines))
            self.stack.setCurrentIndex(3)
        else:
            self.accept()
        self._update_nav()
