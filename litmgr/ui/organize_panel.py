"""论文整理面板：给某篇论文设置标签、分组。

【作用】显示某篇论文当前的标签和所属分组，并提供“编辑”对话框（可勾选已有项，也能直接新建）。
    用在详情窗口顶部；同样的对话框也被主窗口右键菜单“批量打标签/加入分组”复用。
【依赖】services.organize_service（通过 AppContext）；ui.utils。
【被谁调用】ui.detail_window、ui.main_window。
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QLineEdit,
                               QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget)

from ..services.app_context import AppContext
from .utils import guarded


class MultiPickDialog(QDialog):
    """勾选多个已有项，并可输入新项名称（回车或点“新建”加入列表）。"""

    def __init__(self, parent, title: str, items: list[str], checked: set[str],
                 allow_new: bool = True, hint: str = "") -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(340, 420)
        lay = QVBoxLayout(self)
        if hint:
            lay.addWidget(QLabel(hint))
        self.list = QListWidget()
        for name in items:
            self._add(name, name in checked)
        lay.addWidget(self.list)
        if allow_new:
            row = QHBoxLayout()
            self.new_edit = QLineEdit()
            self.new_edit.setPlaceholderText("输入新名称后回车")
            self.new_edit.returnPressed.connect(self._new)
            btn = QPushButton("新建")
            btn.clicked.connect(self._new)
            row.addWidget(self.new_edit)
            row.addWidget(btn)
            lay.addLayout(row)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def _add(self, name: str, checked: bool) -> None:
        it = QListWidgetItem(name)
        it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
        it.setCheckState(Qt.Checked if checked else Qt.Unchecked)
        self.list.addItem(it)

    def _new(self) -> None:
        name = self.new_edit.text().strip()
        if not name:
            return
        for i in range(self.list.count()):
            if self.list.item(i).text() == name:
                self.list.item(i).setCheckState(Qt.Checked)
                break
        else:
            self._add(name, True)
        self.new_edit.clear()

    def selected(self) -> set[str]:
        return {self.list.item(i).text() for i in range(self.list.count())
                if self.list.item(i).checkState() == Qt.Checked}


@guarded
def edit_tags_for(parent, ctx: AppContext, paper_ids: list[int]) -> bool:
    """为一篇或多篇论文编辑标签。单篇：勾选状态=当前标签；多篇：只做“添加”。"""
    all_names = [t.name for t in ctx.organize.tags()]
    single = len(paper_ids) == 1
    current = {t.name for t in ctx.organize.tags_of(paper_ids[0])} if single else set()
    dlg = MultiPickDialog(parent, "编辑标签" if single else f"给 {len(paper_ids)} 篇论文添加标签",
                          all_names, current)
    if dlg.exec() != QDialog.Accepted:
        return False
    chosen = dlg.selected()
    for name in chosen - current:
        ctx.organize.tag_papers(paper_ids, name)
    if single:
        by_name = {t.name: t for t in ctx.organize.tags_of(paper_ids[0])}
        for name in current - chosen:
            ctx.organize.untag_paper(paper_ids[0], by_name[name].id)
    return True


@guarded
def edit_collections_for(parent, ctx: AppContext, paper_ids: list[int]) -> bool:
    """为一篇或多篇论文编辑分组。逻辑同 edit_tags_for。"""
    all_names = [c.name for c in ctx.organize.collections()]
    single = len(paper_ids) == 1
    current = {c.name for c in ctx.organize.collections_of(paper_ids[0])} if single else set()
    dlg = MultiPickDialog(parent, "编辑分组" if single else f"把 {len(paper_ids)} 篇论文加入分组",
                          all_names, current)
    if dlg.exec() != QDialog.Accepted:
        return False
    chosen = dlg.selected()
    by_name = {c.name: c for c in ctx.organize.collections()}
    for name in chosen - current:
        cid = by_name[name].id if name in by_name else ctx.organize.add_collection(name)
        ctx.organize.add_to_collection(paper_ids, cid)
    if single:
        for name in current - chosen:
            ctx.organize.remove_from_collection(paper_ids[0], by_name[name].id)
    return True


class OrganizePanel(QWidget):
    """详情窗口顶部：标签与分组一览 + 编辑按钮。"""

    def __init__(self, ctx: AppContext, paper_id: int, parent=None) -> None:
        super().__init__(parent)
        self.ctx, self.paper_id = ctx, paper_id
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.tag_label = QLabel()
        self.col_label = QLabel()
        for lbl in (self.tag_label, self.col_label):
            lbl.setWordWrap(True)
        b1, b2 = QPushButton("标签…"), QPushButton("分组…")
        b1.clicked.connect(lambda: edit_tags_for(self, ctx, [paper_id]))
        b2.clicked.connect(lambda: edit_collections_for(self, ctx, [paper_id]))
        lay.addWidget(b1)
        lay.addWidget(self.tag_label, 1)
        lay.addWidget(b2)
        lay.addWidget(self.col_label, 1)
        self.refresh()

    def refresh(self) -> None:
        tags = [t.name for t in self.ctx.organize.tags_of(self.paper_id)]
        cols = [c.name for c in self.ctx.organize.collections_of(self.paper_id)]
        self.tag_label.setText("、".join(tags) if tags else "（无标签）")
        self.col_label.setText("、".join(cols) if cols else "（未分组）")
