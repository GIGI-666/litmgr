"""论文字段表单。

【作用】把一篇论文的“所有字段”显示成可编辑表单：按字段分组折叠，每个字段按类型使用
    合适的编辑控件。用户编辑后自动保存（失去焦点即提交），并写入修改历史。
【职责】
    - 按 FieldDef 动态生成表单（字段增删改后可 rebuild）
    - 编辑提交 -> paper_service.set_field，并把规范化后的值回写控件
    - refresh()：外部修改（其他窗口、撤销）后刷新显示，但不覆盖正在输入的控件
    - 显示导入时“待归类内容”，可一键并入某字段或丢弃
【依赖】ui.field_widgets；services（通过 AppContext）。
【被谁调用】ui.detail_window。
"""

from __future__ import annotations

import html

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QFormLayout, QGroupBox, QHBoxLayout, QLabel, QMenu,
                               QPushButton, QScrollArea, QToolButton, QVBoxLayout, QWidget)

from ..services.app_context import AppContext
from .field_widgets import FieldEditor, create_editor
from .utils import guarded


class _CollapsibleGroup(QGroupBox):
    """可折叠的分组框：点标题勾选框折叠/展开。"""

    def __init__(self, title: str) -> None:
        super().__init__(title)
        self.setCheckable(True)
        self.setChecked(True)
        self.body = QWidget()
        self.form = QFormLayout(self.body)
        self.form.setLabelAlignment(Qt.AlignTop)
        self.form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 4, 6, 6)
        lay.addWidget(self.body)
        self.toggled.connect(self.body.setVisible)


class PaperFieldForm(QScrollArea):
    def __init__(self, ctx: AppContext, paper_id: int, parent=None) -> None:
        super().__init__(parent)
        self.ctx, self.paper_id = ctx, paper_id
        self.setWidgetResizable(True)
        self.editors: dict[int, FieldEditor] = {}
        self._collapsed: set[str] = set()
        self.rebuild()

    # ---------- 构建 ----------
    def rebuild(self) -> None:
        """按当前字段定义重建整个表单（字段增删改后调用）。"""
        if self.widget():
            self._collapsed = {g.title() for g in self.widget().findChildren(_CollapsibleGroup)
                               if not g.isChecked()}
        root = QWidget()
        lay = QVBoxLayout(root)
        self.editors.clear()
        self.pending_box = QGroupBox("待归类内容（导入时无法识别的内容）")
        self.pending_lay = QVBoxLayout(self.pending_box)
        lay.addWidget(self.pending_box)

        groups: dict[str, _CollapsibleGroup] = {}
        for f in self.ctx.fields.list():
            title = f.group_name or "其他"
            g = groups.get(title)
            if g is None:
                g = groups[title] = _CollapsibleGroup(title)
                lay.addWidget(g)
            ed = create_editor(f)
            ed.committed.connect(lambda text, fid=f.id: self._on_commit(fid, text))
            label = QLabel(f.name + "：")
            label.setWordWrap(True)
            label.setFixedWidth(150)
            label.setToolTip(f"字段类型：{f.type}")
            g.form.addRow(label, ed)
            self.editors[f.id] = ed
        for title, g in groups.items():
            if title in self._collapsed:
                g.setChecked(False)
        lay.addStretch(1)
        self.setWidget(root)
        self.refresh(force=True)

    # ---------- 刷新 ----------
    def refresh(self, force: bool = False) -> None:
        """从数据库重新读取并显示。正在输入的控件不被覆盖（force=True 时覆盖）。"""
        paper = self.ctx.papers.get(self.paper_id)
        for fid, ed in self.editors.items():
            if not force and ed.is_editing():
                continue
            v = paper.values.get(fid)
            ed.set_text(v.text if v else "")
        self._refresh_pending()

    def _refresh_pending(self) -> None:
        while self.pending_lay.count():
            w = self.pending_lay.takeAt(0).widget()
            if w:
                w.deleteLater()
        items = self.ctx.imports.list_pending(self.paper_id)
        self.pending_box.setVisible(bool(items))
        for p in items:
            row = QWidget()
            h = QHBoxLayout(row)
            h.setContentsMargins(0, 0, 0, 0)
            # QLabel 会把含 < > 的文字当 HTML 解析，所以必须转义
            text = QLabel(f"<b>{html.escape(p.label)}</b>："
                          f"{html.escape(p.content[:200].replace(chr(10), ' '))}")
            text.setWordWrap(True)
            btn = QToolButton()
            btn.setText("归入字段 ▾")
            btn.setPopupMode(QToolButton.InstantPopup)
            menu = QMenu(btn)
            for f in self.ctx.fields.list():
                menu.addAction(f.name, lambda fid=f.id, pid=p.id: self._assign(pid, fid))
            btn.setMenu(menu)
            drop = QPushButton("丢弃")
            drop.clicked.connect(lambda _=False, pid=p.id: self._discard(pid))
            h.addWidget(text, 1)
            h.addWidget(btn)
            h.addWidget(drop)
            self.pending_lay.addWidget(row)

    # ---------- 用户操作 ----------
    @guarded
    def _on_commit(self, field_id: int, text: str) -> None:
        val = self.ctx.papers.set_field(self.paper_id, field_id, text)
        self.editors[field_id].accept_normalized(val.text)

    @guarded
    def _assign(self, pending_id: int, field_id: int) -> None:
        self.ctx.imports.assign_pending(pending_id, field_id)

    @guarded
    def _discard(self, pending_id: int) -> None:
        self.ctx.imports.discard_pending(pending_id)
