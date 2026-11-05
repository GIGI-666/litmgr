"""论文详情窗口。

【作用】查看并编辑一篇论文的全部信息：所有字段、文件、笔记、修改历史、标签与分组。
    可同时打开多个详情窗口（并排对照不同论文）。
【布局】顶部：标题 + 阅读状态 + 星级 + 操作按钮；标签/分组条；
    下方分页：字段 | 文件 | 笔记 | 修改历史。
【同步】订阅事件总线：任意窗口修改了这篇论文，这里自动刷新（不覆盖正在输入的内容）；
    论文被删除时自动关闭。
【依赖】ui.field_form / file_panel / note_panel / history_panel / organize_panel；
    services（通过 AppContext）；窗口管理器（通过参数传入，用于打开阅读器/对比窗口）。
【被谁调用】ui.window_manager.open_detail。
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QComboBox, QHBoxLayout, QLabel, QMainWindow, QMessageBox,
                               QPushButton, QTabWidget, QVBoxLayout, QWidget)

from ..core.events import Events
from ..core.models import READ_STATUS
from ..services.app_context import AppContext
from .field_form import PaperFieldForm
from .file_panel import FilePanel
from .history_panel import HistoryPanel
from .note_panel import NotePanel
from .organize_panel import OrganizePanel
from .utils import EventSubscriberMixin, guarded


class DetailWindow(EventSubscriberMixin, QMainWindow):
    closed = Signal()

    def __init__(self, ctx: AppContext, windows, paper_id: int) -> None:
        super().__init__()
        self.ctx, self.windows, self.paper_id = ctx, windows, paper_id
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.resize(900, 820)

        central = QWidget()
        self.setCentralWidget(central)
        lay = QVBoxLayout(central)

        # 顶部：标题与操作
        self.title_label = QLabel()
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.title_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lay.addWidget(self.title_label)

        bar = QHBoxLayout()
        self.status_combo = QComboBox()
        for key, label in READ_STATUS.items():
            self.status_combo.addItem(label, key)
        self.status_combo.activated.connect(self._on_status)
        self.rating_combo = QComboBox()
        self.rating_combo.addItem("未评分", 0)
        for n in range(1, 6):
            self.rating_combo.addItem("★" * n + "☆" * (5 - n), n)
        self.rating_combo.activated.connect(self._on_rating)
        bar.addWidget(QLabel("阅读状态："))
        bar.addWidget(self.status_combo)
        bar.addWidget(QLabel("星级："))
        bar.addWidget(self.rating_combo)
        bar.addStretch(1)
        for text, fn in (("阅读（PDF + 翻译）", self._read), ("与其他论文对比…", self._compare),
                         ("删除论文", self._delete)):
            b = QPushButton(text)
            b.clicked.connect(lambda _=False, f=fn: f())
            bar.addWidget(b)
        lay.addLayout(bar)

        self.organize_panel = OrganizePanel(ctx, paper_id)
        lay.addWidget(self.organize_panel)

        # 分页
        self.tabs = QTabWidget()
        self.form = PaperFieldForm(ctx, paper_id)
        self.file_panel = FilePanel(ctx, paper_id, windows)
        self.note_panel = NotePanel(ctx, paper_id)
        self.history_panel = HistoryPanel(ctx, paper_id)
        self.tabs.addTab(self.form, "字段")
        self.tabs.addTab(self.file_panel, "文件")
        self.tabs.addTab(self.note_panel, "笔记")
        self.tabs.addTab(self.history_panel, "修改历史")
        lay.addWidget(self.tabs, 1)

        bus = ctx.events
        self.subscribe(bus, Events.PAPER_CHANGED, self._on_paper_changed)
        self.subscribe(bus, Events.PAPER_DELETED, self._on_paper_deleted)
        self.subscribe(bus, Events.FIELDS_CHANGED, self._on_fields_changed)
        self.subscribe(bus, Events.FILES_CHANGED, self._on_files_changed)
        self.subscribe(bus, Events.NOTES_CHANGED, self._on_notes_changed)
        self.subscribe(bus, Events.ORGANIZE_CHANGED, self._on_organize_changed)
        self.subscribe(bus, Events.LIBRARY_CHANGED, self._on_library_changed)
        self._refresh_header()

    # ---------- 顶部 ----------
    def _refresh_header(self) -> None:
        p = self.ctx.papers.get(self.paper_id)
        self.title_label.setText(p.title)
        self.setWindowTitle(f"{p.title} - 论文详情")
        for combo, value in ((self.status_combo, p.read_status), (self.rating_combo, p.rating)):
            combo.blockSignals(True)
            combo.setCurrentIndex(max(combo.findData(value), 0))
            combo.blockSignals(False)

    @guarded
    def _on_status(self, _i: int) -> None:
        self.ctx.papers.set_status(self.paper_id, self.status_combo.currentData())

    @guarded
    def _on_rating(self, _i: int) -> None:
        self.ctx.papers.set_rating(self.paper_id, self.rating_combo.currentData())

    def _read(self) -> None:
        self.windows.open_reader(self.paper_id)

    def _compare(self) -> None:
        self.windows.open_compare([self.paper_id])

    @guarded
    def _delete(self) -> None:
        if QMessageBox.question(
                self, "删除论文",
                "永久删除这篇论文及其库内文件（PDF、翻译等副本）？\n此操作不可撤销。\n"
                "（你原来的源文件不受影响）") == QMessageBox.Yes:
            self.ctx.papers.delete(self.paper_id)

    # ---------- 事件处理 ----------
    def _mine(self, paper_id) -> bool:
        return paper_id is None or paper_id == self.paper_id

    def _on_paper_changed(self, paper_id=None, **_kw) -> None:
        if self._mine(paper_id):
            self._refresh_header()
            self.form.refresh()
            self.organize_panel.refresh()
            self.history_panel.refresh()

    def _on_paper_deleted(self, paper_id=None, **_kw) -> None:
        if paper_id == self.paper_id:
            self.close()

    def _on_fields_changed(self, **_kw) -> None:
        self.form.rebuild()
        self._refresh_header()

    def _on_files_changed(self, paper_id=None, **_kw) -> None:
        if self._mine(paper_id):
            self.file_panel.refresh()

    def _on_notes_changed(self, paper_id=None, **_kw) -> None:
        if self._mine(paper_id):
            self.note_panel.refresh()

    def _on_organize_changed(self, **_kw) -> None:
        self.organize_panel.refresh()

    def _on_library_changed(self, **_kw) -> None:
        if not self.ctx.papers.exists(self.paper_id):
            self.close()
            return
        self._refresh_header()
        self.form.rebuild()
        self.file_panel.refresh()
        self.note_panel.refresh()
        self.history_panel.refresh()
        self.organize_panel.refresh()

    def closeEvent(self, e) -> None:
        self.unsubscribe_all()
        self.closed.emit()
        super().closeEvent(e)
