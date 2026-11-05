"""修改历史面板：查看某篇论文的字段修改记录，并可撤销某一条。

【作用】让你放心地改字段：每次修改都有“旧值 -> 新值”记录，随时可恢复。
【依赖】services.history_service（通过 AppContext）。
【被谁调用】ui.detail_window。
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

from ..services.app_context import AppContext
from .utils import add_buttons, guarded


def _short(s: str, n: int = 60) -> str:
    s = s.replace("\n", " ")
    return s if len(s) <= n else s[:n] + "…"


class HistoryPanel(QWidget):
    def __init__(self, ctx: AppContext, paper_id: int, parent=None) -> None:
        super().__init__(parent)
        self.ctx, self.paper_id = ctx, paper_id
        lay = QVBoxLayout(self)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["时间", "字段", "旧值", "新值", "状态"])
        self.tree.setRootIsDecorated(False)
        self.tree.setColumnWidth(0, 140)
        self.tree.setColumnWidth(1, 150)
        self.tree.setColumnWidth(2, 220)
        self.tree.setColumnWidth(3, 220)
        lay.addWidget(self.tree)
        add_buttons(lay, [("撤销选中的修改（恢复旧值）", self.undo_selected)])
        self.refresh()

    def refresh(self) -> None:
        self.tree.clear()
        for e in self.ctx.history.of_paper(self.paper_id):
            it = QTreeWidgetItem([e.changed_at, e.field_name, _short(e.old_value),
                                  _short(e.new_value), "已撤销" if e.undone else ""])
            it.setData(0, Qt.UserRole, e.id)
            it.setToolTip(2, e.old_value)
            it.setToolTip(3, e.new_value)
            self.tree.addTopLevelItem(it)

    @guarded
    def undo_selected(self) -> None:
        it = self.tree.currentItem()
        if it:
            self.ctx.history.undo(it.data(0, Qt.UserRole))
            self.refresh()   # 撤销事件发布时记录尚未标记为“已撤销”，这里再刷新一次
