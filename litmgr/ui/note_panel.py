"""笔记面板：一篇论文的多条阅读笔记。

【作用】在详情窗口里写/改/删笔记，笔记可被全文检索。
【依赖】services.note_service（通过 AppContext）。
【被谁调用】ui.detail_window。
"""

from __future__ import annotations

from PySide6.QtWidgets import (QHBoxLayout, QListWidget, QListWidgetItem, QMessageBox,
                               QPlainTextEdit, QPushButton, QSplitter, QVBoxLayout, QWidget)
from PySide6.QtCore import Qt

from ..services.app_context import AppContext
from .utils import guarded


class NotePanel(QWidget):
    def __init__(self, ctx: AppContext, paper_id: int, parent=None) -> None:
        super().__init__(parent)
        self.ctx, self.paper_id = ctx, paper_id
        self._current_id: int | None = None
        lay = QVBoxLayout(self)
        split = QSplitter(Qt.Vertical)
        self.list = QListWidget()
        self.list.currentItemChanged.connect(self._on_select)
        self.edit = QPlainTextEdit()
        self.edit.setPlaceholderText("在这里写笔记/摘录，点“保存”。选中上方历史笔记可编辑。")
        split.addWidget(self.list)
        split.addWidget(self.edit)
        split.setSizes([160, 220])
        lay.addWidget(split)
        row = QHBoxLayout()
        for text, fn in (("新笔记", self.new_note), ("保存", self.save), ("删除", self.delete)):
            b = QPushButton(text)
            b.clicked.connect(lambda _=False, f=fn: f())
            row.addWidget(b)
        row.addStretch(1)
        lay.addLayout(row)
        self.refresh()

    def refresh(self) -> None:
        keep = self._current_id
        self.list.blockSignals(True)
        self.list.clear()
        for n in self.ctx.notes.list(self.paper_id):
            first = n.content.strip().splitlines()[0][:50] if n.content.strip() else "（空）"
            it = QListWidgetItem(f"{n.updated_at[:16]}  {first}")
            it.setData(Qt.UserRole, (n.id, n.content))
            self.list.addItem(it)
            if n.id == keep:
                self.list.setCurrentItem(it)
        self.list.blockSignals(False)

    def _on_select(self, cur, _prev) -> None:
        if cur is None:
            return
        self._current_id, content = cur.data(Qt.UserRole)
        self.edit.setPlainText(content)

    def new_note(self) -> None:
        self._current_id = None
        self.list.clearSelection()
        self.edit.clear()
        self.edit.setFocus()

    @guarded
    def save(self) -> None:
        text = self.edit.toPlainText()
        if self._current_id is None:
            self._current_id = self.ctx.notes.add(self.paper_id, text)
        else:
            self.ctx.notes.update(self._current_id, self.paper_id, text)

    @guarded
    def delete(self) -> None:
        if self._current_id is not None and QMessageBox.question(
                self, "删除笔记", "确定删除这条笔记？") == QMessageBox.Yes:
            self.ctx.notes.delete(self._current_id, self.paper_id)
            self.new_note()
