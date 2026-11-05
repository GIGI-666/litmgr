"""阅读窗口：PDF 与翻译左右并排对照。

【作用】阅读一篇论文：左边 PDF（可选正文/补充材料等多个 PDF），右边翻译 md（含公式）。
    两边可单独隐藏（只看 PDF 或只看翻译），也可用系统默认程序打开 PDF。
    不同论文可各开一个阅读窗口并排比较。
【同步】订阅事件：论文文件增删时刷新文件列表；论文删除时自动关闭。
【阅读历史】打开时登记到“最近阅读”；关闭时保存页面状态（capture_state），
    之后从历史记录打开会带着这份状态（apply_state）还原到关闭时的样子。
【依赖】ui.pdf_viewer / md_viewer；services.paper_service、reading_history_service（通过 AppContext）。
【被谁调用】ui.window_manager.open_reader。
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QByteArray, Qt, QTimer, Signal
from PySide6.QtWidgets import (QCheckBox, QComboBox, QHBoxLayout, QLabel, QMainWindow,
                               QPushButton, QSplitter, QVBoxLayout, QWidget)

from ..core.events import Events
from ..core.models import KIND_PDF, KIND_TRANSLATION
from ..services.app_context import AppContext
from .md_viewer import MarkdownViewer
from .pdf_viewer import PdfViewer
from .utils import EventSubscriberMixin, guarded, open_path

log = logging.getLogger(__name__)


class ReaderWindow(EventSubscriberMixin, QMainWindow):
    closed = Signal()

    def __init__(self, ctx: AppContext, windows, paper_id: int, file_id: int | None = None,
                 restore_state: dict | None = None) -> None:
        super().__init__()
        self.ctx, self.windows, self.paper_id = ctx, windows, paper_id
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.resize(1500, 900)

        central = QWidget()
        self.setCentralWidget(central)
        lay = QVBoxLayout(central)
        lay.setContentsMargins(6, 6, 6, 6)

        bar = QHBoxLayout()
        self.pdf_box = QComboBox()
        self.md_box = QComboBox()
        self.pdf_box.setMinimumWidth(260)
        self.md_box.setMinimumWidth(260)
        self.pdf_box.activated.connect(lambda _i: self._load_pdf())
        self.md_box.activated.connect(lambda _i: self._load_md())
        self.show_pdf = QCheckBox("显示 PDF")
        self.show_md = QCheckBox("显示翻译")
        for cb in (self.show_pdf, self.show_md):
            cb.setChecked(True)
            cb.toggled.connect(self._apply_visibility)
        ext = QPushButton("用系统程序打开 PDF")
        ext.clicked.connect(self._open_external)
        bar.addWidget(QLabel("PDF："))
        bar.addWidget(self.pdf_box)
        bar.addWidget(QLabel("翻译："))
        bar.addWidget(self.md_box)
        bar.addWidget(self.show_pdf)
        bar.addWidget(self.show_md)
        bar.addStretch(1)
        bar.addWidget(ext)
        lay.addLayout(bar)

        self.split = QSplitter(Qt.Horizontal)
        self.pdf = PdfViewer()
        self.md = MarkdownViewer()
        self.split.addWidget(self.pdf)
        self.split.addWidget(self.md)
        self.split.setSizes([750, 750])
        lay.addWidget(self.split, 1)

        self.subscribe(ctx.events, Events.FILES_CHANGED, self._on_files_changed)
        self.subscribe(ctx.events, Events.PAPER_DELETED, self._on_deleted)
        self.subscribe(ctx.events, Events.PAPER_CHANGED, self._on_paper_changed)
        self._reload_lists()
        if file_id is not None:
            self.show_file(file_id)
        if restore_state:
            self._select_files_from_state(restore_state)
        self._load_pdf()
        self._load_md()
        self._update_title()
        if restore_state:
            self.apply_state(restore_state)
        # 记入“最近阅读”（保留这篇论文上次关闭时的状态，直到本次关闭时覆盖）
        self.ctx.reading.record_open(self.paper_id)

    # ---------- 阅读状态：保存与还原 ----------
    def capture_state(self) -> dict:
        """收集当前页面状态：选了哪些文件、显示哪几栏、两栏比例、PDF 页码/缩放、翻译滚动位置、窗口位置大小。"""
        return {
            "pdf_file": self.pdf_box.currentData(),
            "md_file": self.md_box.currentData(),
            "show_pdf": self.show_pdf.isChecked(),
            "show_md": self.show_md.isChecked(),
            "sizes": self.split.sizes(),
            "pdf": self.pdf.get_state(),
            "md": self.md.get_state(),
            "geometry": bytes(self.saveGeometry().toBase64()).decode("ascii"),
        }

    def _select_files_from_state(self, st: dict) -> None:
        """在加载前选中上次看的 PDF/翻译（文件已被删除则保持默认）。"""
        for box, key in ((self.pdf_box, "pdf_file"), (self.md_box, "md_file")):
            i = box.findData(st.get(key))
            if i >= 0:
                box.setCurrentIndex(i)

    def apply_state(self, st: dict) -> None:
        """还原窗口与两个查看器的状态（文件选择已在加载前完成）。"""
        geo = st.get("geometry")
        if geo:
            self.restoreGeometry(QByteArray.fromBase64(geo.encode("ascii")))
        for cb, key in ((self.show_pdf, "show_pdf"), (self.show_md, "show_md")):
            if cb.isEnabled() and key in st:
                cb.setChecked(bool(st[key]))
        sizes = st.get("sizes")
        if isinstance(sizes, list) and len(sizes) == 2 and sum(sizes) > 0:
            # 窗口显示出来、宽度确定之后，按保存时的比例分配两栏宽度
            total = float(sum(sizes))
            ratio = [s / total for s in sizes]
            QTimer.singleShot(0, self, lambda: self._apply_split_ratio(ratio))
        self.pdf.apply_state(st.get("pdf") or {})
        self.md.apply_state(st.get("md") or {})

    def _apply_split_ratio(self, ratio: list[float]) -> None:
        total = max(self.split.width(), 2)
        self.split.setSizes([int(total * r) for r in ratio])

    # ---------- 文件列表 ----------
    def _reload_lists(self) -> None:
        cur_pdf, cur_md = self.pdf_box.currentData(), self.md_box.currentData()
        self.pdf_box.clear()
        self.md_box.clear()
        for f in self.ctx.papers.list_files(self.paper_id):
            if f.kind == KIND_PDF:
                self.pdf_box.addItem(f"[{f.subtype or 'PDF'}] {f.display_name}", f.id)
            elif f.kind == KIND_TRANSLATION:
                self.md_box.addItem(f.display_name, f.id)
        self.pdf_box.setCurrentIndex(max(self.pdf_box.findData(cur_pdf), 0))
        self.md_box.setCurrentIndex(max(self.md_box.findData(cur_md), 0))
        self.show_pdf.setEnabled(self.pdf_box.count() > 0)
        self.show_md.setEnabled(self.md_box.count() > 0)
        self._apply_visibility()
        # 当前正在看的文件被移除/换成别的文件时，重新加载
        if self.pdf_box.currentData() != cur_pdf and self.pdf_box.count():
            self._load_pdf()
        if self.md_box.currentData() != cur_md and self.md_box.count():
            self._load_md()

    def _apply_visibility(self, *_a) -> None:
        self.pdf.setVisible(self.show_pdf.isChecked() and self.pdf_box.count() > 0)
        self.md.setVisible(self.show_md.isChecked() and self.md_box.count() > 0)

    def show_file(self, file_id: int) -> None:
        """切换到指定文件（PDF 或翻译）。"""
        for box, loader, cb in ((self.pdf_box, self._load_pdf, self.show_pdf),
                                (self.md_box, self._load_md, self.show_md)):
            i = box.findData(file_id)
            if i >= 0:
                box.setCurrentIndex(i)
                cb.setChecked(True)
                loader()

    # ---------- 加载 ----------
    @guarded
    def _load_pdf(self) -> None:
        fid = self.pdf_box.currentData()
        if fid is None:
            return
        f = next(x for x in self.ctx.papers.list_files(self.paper_id) if x.id == fid)
        self.pdf.load(str(self.ctx.papers.abs_path(f)))

    @guarded
    def _load_md(self) -> None:
        fid = self.md_box.currentData()
        if fid is None:
            return
        f = next(x for x in self.ctx.papers.list_files(self.paper_id) if x.id == fid)
        try:
            self.md.load_text(self.ctx.papers.read_text(f))
        except OSError as e:
            self.md.show_message(f"无法读取翻译文件：{e}")

    @guarded
    def _open_external(self) -> None:
        fid = self.pdf_box.currentData()
        if fid is not None:
            f = next(x for x in self.ctx.papers.list_files(self.paper_id) if x.id == fid)
            open_path(self.ctx.papers.abs_path(f))

    def _update_title(self) -> None:
        self.setWindowTitle(f"阅读 - {self.ctx.papers.get(self.paper_id).title}")

    # ---------- 事件 ----------
    def _on_files_changed(self, paper_id=None, **_kw) -> None:
        if paper_id in (None, self.paper_id):
            self._reload_lists()

    def _on_paper_changed(self, paper_id=None, **_kw) -> None:
        if paper_id in (None, self.paper_id) and self.ctx.papers.exists(self.paper_id):
            self._update_title()

    def _on_deleted(self, paper_id=None, **_kw) -> None:
        if paper_id == self.paper_id:
            self.close()

    def closeEvent(self, e) -> None:
        # 关闭前保存页面状态，供“最近阅读”还原；保存失败不能阻止窗口关闭
        try:
            self.ctx.reading.save_state(self.paper_id, self.capture_state())
        except Exception:  # noqa: BLE001
            log.exception("保存阅读状态失败")
        self.unsubscribe_all()
        self.closed.emit()
        super().closeEvent(e)
