"""论文对比窗口。

【作用】把多篇论文的字段并排成一张表：列=论文，行=字段，一眼看出异同。
【功能】
    - 可随时添加/移除要对比的论文，勾选要对比的字段
    - “只显示有差异的字段”“隐藏全部为空的字段”
    - 有差异的字段行以浅黄色标出
    - 双击单元格可直接修改字段内容（自动保存、记入修改历史）
    - 双击列标题打开该论文详情；可导出为 CSV / Markdown
    - 可同时开多个对比窗口
【同步】订阅事件：字段/论文变化时自动刷新。
【依赖】services.compare_service / export_service（通过 AppContext）。
【被谁调用】ui.window_manager.open_compare。
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QDialog, QDialogButtonBox,
                               QFileDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QMainWindow, QPlainTextEdit, QPushButton,
                               QSplitter, QStyledItemDelegate, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)

from ..core.events import Events
from ..services.app_context import AppContext
from .utils import EventSubscriberMixin, guarded

DIFF_BG = QBrush(QColor("#fff6d6"))
MAX_ROW_HEIGHT = 420


class PaperPickerDialog(QDialog):
    """从全库选择要加入对比的论文（可搜索、多选）。"""

    def __init__(self, parent, ctx: AppContext, exclude: set[int]) -> None:
        super().__init__(parent)
        self.setWindowTitle("选择要加入对比的论文")
        self.resize(560, 520)
        lay = QVBoxLayout(self)
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("输入关键词过滤标题…")
        self.filter.textChanged.connect(self._apply_filter)
        lay.addWidget(self.filter)
        self.list = QListWidget()
        self.list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        for p in ctx.papers.list_titles():
            if p.id not in exclude:
                it = QListWidgetItem(p.title)
                it.setData(Qt.UserRole, p.id)
                self.list.addItem(it)
        lay.addWidget(self.list)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def _apply_filter(self, text: str) -> None:
        t = text.strip().casefold()
        for i in range(self.list.count()):
            self.list.item(i).setHidden(bool(t) and t not in self.list.item(i).text().casefold())

    def selected_ids(self) -> list[int]:
        return [it.data(Qt.UserRole) for it in self.list.selectedItems()]


class _MultilineDelegate(QStyledItemDelegate):
    """单元格编辑使用多行文本框（保留换行）。"""

    def createEditor(self, parent, option, index):
        ed = QPlainTextEdit(parent)
        ed.setTabChangesFocus(True)
        return ed

    def setEditorData(self, editor, index) -> None:
        editor.setPlainText(index.data(Qt.EditRole) or "")

    def setModelData(self, editor, model, index) -> None:
        model.setData(index, editor.toPlainText(), Qt.EditRole)

    def updateEditorGeometry(self, editor, option, index) -> None:
        r = option.rect
        editor.setGeometry(r.x(), r.y(), r.width(), max(r.height(), 140))


class CompareWindow(EventSubscriberMixin, QMainWindow):
    closed = Signal()

    def __init__(self, ctx: AppContext, windows, paper_ids: list[int]) -> None:
        super().__init__()
        self.ctx, self.windows = ctx, windows
        self.paper_ids = list(paper_ids)
        self._populating = False
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowTitle("论文对比")
        self.resize(1500, 900)

        split = QSplitter(Qt.Horizontal)
        self.setCentralWidget(split)

        # 左侧：论文 + 字段 + 选项
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.addWidget(QLabel("<b>对比的论文</b>"))
        self.paper_list = QListWidget()
        self.paper_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        ll.addWidget(self.paper_list, 1)
        row = QHBoxLayout()
        add_b, rm_b = QPushButton("添加论文…"), QPushButton("移除选中")
        add_b.clicked.connect(self._add_papers)
        rm_b.clicked.connect(self._remove_papers)
        row.addWidget(add_b)
        row.addWidget(rm_b)
        ll.addLayout(row)
        ll.addWidget(QLabel("<b>对比的字段</b>"))
        self.field_list = QListWidget()
        ll.addWidget(self.field_list, 2)
        frow = QHBoxLayout()
        all_b, none_b = QPushButton("全选"), QPushButton("全不选")
        all_b.clicked.connect(lambda: self._check_all(True))
        none_b.clicked.connect(lambda: self._check_all(False))
        frow.addWidget(all_b)
        frow.addWidget(none_b)
        ll.addLayout(frow)
        self.only_diff = QCheckBox("只显示有差异的字段")
        self.hide_empty = QCheckBox("隐藏全部为空的字段")
        self.hide_empty.setChecked(True)
        ll.addWidget(self.only_diff)
        ll.addWidget(self.hide_empty)
        exp_row = QHBoxLayout()
        csv_b, md_b = QPushButton("导出 CSV"), QPushButton("导出 Markdown")
        csv_b.clicked.connect(lambda: self._export("csv"))
        md_b.clicked.connect(lambda: self._export("md"))
        exp_row.addWidget(csv_b)
        exp_row.addWidget(md_b)
        ll.addLayout(exp_row)
        split.addWidget(left)

        # 右侧：对比表
        self.table = QTableWidget()
        self.table.setWordWrap(True)
        self.table.setItemDelegate(_MultilineDelegate(self.table))
        self.table.setAlternatingRowColors(False)
        self.table.setTextElideMode(Qt.ElideRight)
        self.table.horizontalHeader().setSectionsClickable(True)
        self.table.horizontalHeader().sectionDoubleClicked.connect(self._open_paper)
        self.table.verticalHeader().setMaximumWidth(220)
        self.table.itemChanged.connect(self._on_item_changed)
        split.addWidget(self.table)
        split.setSizes([300, 1200])

        self._reload_field_list()
        self.only_diff.toggled.connect(lambda _=None: self.rebuild())
        self.hide_empty.toggled.connect(lambda _=None: self.rebuild())
        self.field_list.itemChanged.connect(lambda _it: self.rebuild())

        bus = ctx.events
        self.subscribe(bus, Events.PAPER_CHANGED, self._on_data_changed)
        self.subscribe(bus, Events.PAPER_DELETED, self._on_paper_deleted)
        self.subscribe(bus, Events.FIELDS_CHANGED, self._on_fields_changed)
        self.subscribe(bus, Events.LIBRARY_CHANGED, self._on_data_changed)
        self.rebuild()

    # ---------- 字段列表 ----------
    def _reload_field_list(self) -> None:
        checked = {self.field_list.item(i).data(Qt.UserRole)
                   for i in range(self.field_list.count())
                   if self.field_list.item(i).checkState() == Qt.Checked}
        first = self.field_list.count() == 0
        self.field_list.blockSignals(True)
        self.field_list.clear()
        for f in self.ctx.fields.list():
            it = QListWidgetItem(f.name)
            it.setData(Qt.UserRole, f.id)
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Checked if (first or f.id in checked) else Qt.Unchecked)
            self.field_list.addItem(it)
        self.field_list.blockSignals(False)

    def _check_all(self, on: bool) -> None:
        self.field_list.blockSignals(True)
        for i in range(self.field_list.count()):
            self.field_list.item(i).setCheckState(Qt.Checked if on else Qt.Unchecked)
        self.field_list.blockSignals(False)
        self.rebuild()

    def _selected_field_ids(self) -> list[int]:
        return [self.field_list.item(i).data(Qt.UserRole) for i in range(self.field_list.count())
                if self.field_list.item(i).checkState() == Qt.Checked]

    # ---------- 论文管理 ----------
    @guarded
    def _add_papers(self) -> None:
        dlg = PaperPickerDialog(self, self.ctx, set(self.paper_ids))
        if dlg.exec() == QDialog.Accepted:
            self.paper_ids += dlg.selected_ids()
            self.rebuild()

    def _remove_papers(self) -> None:
        drop = {it.data(Qt.UserRole) for it in self.paper_list.selectedItems()}
        self.paper_ids = [i for i in self.paper_ids if i not in drop]
        self.rebuild()

    def _open_paper(self, col: int) -> None:
        if 0 <= col < len(self.paper_ids):
            self.windows.open_detail(self.paper_ids[col])

    # ---------- 构建对比表 ----------
    def _current_table(self):
        table = self.ctx.compare.build(self.paper_ids, self._selected_field_ids())
        if self.hide_empty.isChecked():
            table = table.hide_empty()
        if self.only_diff.isChecked():
            table = table.only_different()
        return table

    @guarded
    def rebuild(self) -> None:
        # 先剔除已不存在的论文
        self.paper_ids = [i for i in self.paper_ids if self.ctx.papers.exists(i)]
        table = self._current_table()
        self._populating = True
        try:
            self.paper_list.clear()
            for p in table.papers:
                it = QListWidgetItem(p.title)
                it.setData(Qt.UserRole, p.id)
                self.paper_list.addItem(it)
            self.table.clear()
            self.table.setColumnCount(len(table.papers))
            self.table.setRowCount(len(table.rows))
            self.table.setHorizontalHeaderLabels([p.title for p in table.papers])
            self.table.setVerticalHeaderLabels([r.field.name for r in table.rows])
            for c in range(len(table.papers)):
                self.table.setColumnWidth(c, 380)
            for r, row in enumerate(table.rows):
                for c, text in enumerate(row.cells):
                    it = QTableWidgetItem(text)
                    it.setData(Qt.UserRole, (table.papers[c].id, row.field.id))
                    it.setToolTip(text[:1500])
                    it.setTextAlignment(Qt.AlignLeft | Qt.AlignTop)
                    if not row.all_same:
                        it.setBackground(DIFF_BG)
                    self.table.setItem(r, c, it)
            self.table.resizeRowsToContents()
            for r in range(self.table.rowCount()):
                if self.table.rowHeight(r) > MAX_ROW_HEIGHT:
                    self.table.setRowHeight(r, MAX_ROW_HEIGHT)
        finally:
            self._populating = False

    @guarded
    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._populating:
            return
        pid, fid = item.data(Qt.UserRole)
        self.ctx.papers.set_field(pid, fid, item.text())

    # ---------- 导出 ----------
    @guarded
    def _export(self, fmt: str) -> None:
        if not self.paper_ids:
            return
        filt = "CSV 文件 (*.csv)" if fmt == "csv" else "Markdown (*.md)"
        path, _ = QFileDialog.getSaveFileName(self, "导出对比表", f"论文对比.{fmt}", filt)
        if path:
            self.ctx.export.export_compare(self._current_table(), path, fmt)

    # ---------- 事件 ----------
    def _defer_rebuild(self) -> None:
        QTimer.singleShot(0, self.rebuild)   # 编辑单元格时触发的事件，等编辑流程结束后再刷新

    def _on_data_changed(self, **_kw) -> None:
        self._defer_rebuild()

    def _on_paper_deleted(self, paper_id=None, **_kw) -> None:
        self.paper_ids = [i for i in self.paper_ids if i != paper_id]
        self._defer_rebuild()

    def _on_fields_changed(self, **_kw) -> None:
        self._reload_field_list()
        self._defer_rebuild()

    def closeEvent(self, e) -> None:
        self.unsubscribe_all()
        self.closed.emit()
        super().closeEvent(e)
