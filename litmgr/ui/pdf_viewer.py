"""内置 PDF 查看器。

【作用】在窗口内查看 PDF：翻页/跳页、缩放（适应宽度/整页/自定义）、全文搜索并在结果间跳转。
【实现】基于 Qt 自带的 QtPdf（QPdfDocument + QPdfView + QPdfSearchModel），无需额外依赖、完全离线。
【依赖】PySide6.QtPdf / QtPdfWidgets。
【被谁调用】ui.reader_window。
"""

from __future__ import annotations

from PySide6.QtCore import QModelIndex, QPointF, Qt, QTimer
from PySide6.QtPdf import QPdfDocument, QPdfSearchModel
from PySide6.QtPdfWidgets import QPdfView
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QLineEdit, QPushButton, QSpinBox,
                               QVBoxLayout, QWidget)

from .utils import make_button


class PdfViewer(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.doc = QPdfDocument(self)
        self.view = QPdfView(self)
        self.view.setDocument(self.doc)
        self.view.setPageMode(QPdfView.PageMode.MultiPage)
        self.view.setZoomMode(QPdfView.ZoomMode.FitToWidth)
        self.search_model = QPdfSearchModel(self)
        self.search_model.setDocument(self.doc)
        self.view.setSearchModel(self.search_model)
        self._hit = -1

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        bar = QHBoxLayout()
        self.page_spin = QSpinBox()
        self.page_spin.setMinimum(1)
        self.page_spin.setKeyboardTracking(False)
        self.page_spin.valueChanged.connect(self._jump)
        self.page_total = QLabel("/ 0")
        bar.addWidget(QLabel("页："))
        bar.addWidget(self.page_spin)
        bar.addWidget(self.page_total)
        for text, fn, tip in (("－", self.zoom_out, "缩小"), ("＋", self.zoom_in, "放大"),
                              ("适应宽度", self.fit_width, ""), ("整页", self.fit_page, "")):
            bar.addWidget(make_button(text, fn, tip))
        bar.addStretch(1)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("在 PDF 中搜索（回车）")
        self.search_edit.setMaximumWidth(220)
        self.search_edit.returnPressed.connect(self._search)
        self.search_info = QLabel("")
        prev_b, next_b = QPushButton("↑"), QPushButton("↓")
        prev_b.clicked.connect(lambda: self._goto_hit(-1))
        next_b.clicked.connect(lambda: self._goto_hit(+1))
        for w in (self.search_edit, prev_b, next_b, self.search_info):
            bar.addWidget(w)
        lay.addLayout(bar)
        lay.addWidget(self.view, 1)

        self.view.pageNavigator().currentPageChanged.connect(self._on_page_changed)

    # ---------- 加载 ----------
    def load(self, path: str) -> bool:
        """加载 PDF，成功返回 True。"""
        self.search_model.setSearchString("")
        err = self.doc.load(path)
        ok = err == QPdfDocument.Error.None_
        n = self.doc.pageCount() if ok else 0
        self.page_spin.blockSignals(True)
        self.page_spin.setMaximum(max(n, 1))
        self.page_spin.setValue(1)
        self.page_spin.blockSignals(False)
        self.page_total.setText(f"/ {n}")
        self.search_info.setText("" if ok else "无法打开此 PDF")
        return ok

    # ---------- 翻页与缩放 ----------
    def _jump(self, page: int) -> None:
        self.view.pageNavigator().jump(page - 1, QPointF(0, 0), 0)

    def _on_page_changed(self, page: int) -> None:
        self.page_spin.blockSignals(True)
        self.page_spin.setValue(page + 1)
        self.page_spin.blockSignals(False)

    def zoom_in(self) -> None:
        self.view.setZoomMode(QPdfView.ZoomMode.Custom)
        self.view.setZoomFactor(self.view.zoomFactor() * 1.2)

    def zoom_out(self) -> None:
        self.view.setZoomMode(QPdfView.ZoomMode.Custom)
        self.view.setZoomFactor(self.view.zoomFactor() / 1.2)

    def fit_width(self) -> None:
        self.view.setZoomMode(QPdfView.ZoomMode.FitToWidth)

    def fit_page(self) -> None:
        self.view.setZoomMode(QPdfView.ZoomMode.FitInView)

    # ---------- 阅读状态（供“阅读历史”保存/还原） ----------
    def get_state(self) -> dict:
        """当前阅读位置：页码、页内位置、缩放方式与倍数。"""
        nav = self.view.pageNavigator()
        loc = nav.currentLocation()
        return {"page": nav.currentPage(), "x": loc.x(), "y": loc.y(),
                "zoom_mode": self.view.zoomMode().name, "zoom": self.view.zoomFactor()}

    def apply_state(self, state: dict) -> None:
        """还原阅读位置。需在 load() 之后调用；窗口布局完成后才能准确跳转，所以稍作延迟。"""
        if not state or self.doc.pageCount() == 0:
            return
        mode = getattr(QPdfView.ZoomMode, str(state.get("zoom_mode", "")), None)
        if mode is not None:
            self.view.setZoomMode(mode)
            if mode == QPdfView.ZoomMode.Custom:
                self.view.setZoomFactor(float(state.get("zoom", 1.0)))
        page = max(0, min(int(state.get("page", 0)), self.doc.pageCount() - 1))
        pos = QPointF(float(state.get("x", 0)), float(state.get("y", 0)))
        # 以 self 作为上下文：窗口若在延迟期间被销毁，回调会自动取消
        QTimer.singleShot(250, self, lambda: self._restore_position(page, pos))

    def _restore_position(self, page: int, pos: QPointF) -> None:
        # 窗口可能在延迟期间被关闭/换了文档
        if self.doc.pageCount() > page:
            self.view.pageNavigator().jump(page, pos, 0)

    # ---------- 搜索 ----------
    def _search(self) -> None:
        self.search_model.setSearchString(self.search_edit.text().strip())
        self._hit = -1
        # 搜索是异步的，稍后结果数才会更新
        self.search_model.rowsInserted.connect(self._first_hit, Qt.UniqueConnection)

    def _hit_count(self) -> int:
        # PySide6 里 QAbstractItemModel.rowCount 必须显式传入父索引，不能无参调用
        return self.search_model.rowCount(QModelIndex())

    def _first_hit(self, *_a) -> None:
        if self._hit == -1 and self._hit_count() > 0:
            self._goto_hit(+1)

    def _goto_hit(self, step: int) -> None:
        n = self._hit_count()
        if n == 0:
            self.search_info.setText("无结果" if self.search_edit.text().strip() else "")
            return
        self._hit = (self._hit + step) % n
        link = self.search_model.resultAtIndex(self._hit)
        self.view.pageNavigator().jump(link.page(), link.location(), 0)
        self.view.setCurrentSearchResultIndex(self._hit)
        self.search_info.setText(f"{self._hit + 1}/{n}")
