"""笔记面板：一篇论文的多条阅读笔记。

【作用】在详情窗口里写/改/删笔记，笔记可被全文检索。
【防丢失】正在编辑但还没点“保存”的内容，在切换到别的笔记、点“新笔记”、
    关闭详情窗口时会自动保存（内容为空时不会自动保存，避免误清空已有笔记）。
【依赖】services.note_service（通过 AppContext）。
【被谁调用】ui.detail_window。
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QListWidget, QListWidgetItem, QMessageBox, QPlainTextEdit,
                               QSplitter, QVBoxLayout, QWidget)

from ..services.app_context import AppContext
from .utils import add_buttons, guarded


class NotePanel(QWidget):
    def __init__(self, ctx: AppContext, paper_id: int, parent=None) -> None:
        super().__init__(parent)
        self.ctx, self.paper_id = ctx, paper_id
        self._current_id: int | None = None
        self._baseline = ""        # 编辑框里“已保存/刚载入”的文本，用来判断有没有未保存的修改
        lay = QVBoxLayout(self)
        split = QSplitter(Qt.Vertical)
        self.list = QListWidget()
        self.list.currentItemChanged.connect(self._on_select)
        self.edit = QPlainTextEdit()
        self.edit.setPlaceholderText("在这里写笔记/摘录。切换笔记或关闭窗口时会自动保存。")
        split.addWidget(self.list)
        split.addWidget(self.edit)
        split.setSizes([160, 220])
        lay.addWidget(split)
        add_buttons(lay, [("新笔记", self.new_note), ("保存", self.save), ("删除", self.delete)])
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

    # ---------- 未保存修改的处理 ----------
    def _dirty(self) -> bool:
        text = self.edit.toPlainText()
        return bool(text.strip()) and text != self._baseline

    def _write(self, note_id: int | None, text: str) -> int | None:
        """保存一段文本：note_id 为 None 表示新建。返回笔记 id。"""
        if note_id is None:
            return self.ctx.notes.add(self.paper_id, text)
        self.ctx.notes.update(note_id, self.paper_id, text)
        return note_id

    @guarded
    def flush(self) -> None:
        """把未保存的修改保存起来（关闭窗口、新建笔记前调用）。"""
        if self._dirty() and self.ctx.papers.exists(self.paper_id):   # 论文已被删除时无需保存
            self._current_id = self._write(self._current_id, self.edit.toPlainText())
            self._baseline = self.edit.toPlainText()

    # ---------- 选择 ----------
    def _show(self, note_id: int | None, content: str) -> None:
        self._current_id = note_id
        self._baseline = content
        self.edit.setPlainText(content)

    def _on_select(self, cur, _prev) -> None:
        if cur is None:
            return
        new_id, content = cur.data(Qt.UserRole)
        if self._dirty():
            # 先保存正在编辑的内容再切换。保存会触发列表刷新，所以延后到本次信号处理结束之后
            pending = (self._current_id, self.edit.toPlainText())
            QTimer.singleShot(0, self, lambda: self._save_then_show(pending, new_id))
            return
        self._show(new_id, content)

    @guarded
    def _save_then_show(self, pending: tuple[int | None, str], new_id: int) -> None:
        self._current_id = new_id          # 让刷新后的列表保持选中目标笔记
        self._write(*pending)
        note = next((n for n in self.ctx.notes.list(self.paper_id) if n.id == new_id), None)
        self._show(new_id, note.content if note else "")

    # ---------- 按钮 ----------
    def new_note(self) -> None:
        self.flush()
        self._show(None, "")
        self.list.clearSelection()
        self.edit.setFocus()

    @guarded
    def save(self) -> None:
        text = self.edit.toPlainText()
        self._current_id = self._write(self._current_id, text)
        self._baseline = text

    @guarded
    def delete(self) -> None:
        if self._current_id is not None and QMessageBox.question(
                self, "删除笔记", "确定删除这条笔记？") == QMessageBox.Yes:
            self.ctx.notes.delete(self._current_id, self.paper_id)
            self._show(None, "")
            self.list.clearSelection()
