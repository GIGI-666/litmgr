"""论文文件面板：管理一篇论文的卡片、PDF、翻译、附件。

【作用】列出论文所有文件，支持：双击/按钮打开（PDF 与翻译用内置阅读器，其他用系统程序）、
    用系统程序打开、添加文件（自动判断种类）、删除、修改 PDF 子类型（正文/补充材料/附录）。
【依赖】services（通过 AppContext）；importers.file_pairing.classify（判断新文件种类）；
    ui.window_manager（打开阅读器，作为参数传入，避免循环依赖）。
【被谁调用】ui.detail_window。
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QFileDialog, QInputDialog, QMessageBox,
                               QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from ..core.models import (KIND_ATTACHMENT, KIND_CARD, KIND_LABELS, KIND_PDF, KIND_TRANSLATION,
                           SUBTYPE_APPENDIX, SUBTYPE_MAIN, SUBTYPE_SUPPLEMENT)
from ..importers.file_pairing import classify
from ..services.app_context import AppContext
from .utils import add_buttons, guarded, open_path


class FilePanel(QWidget):
    def __init__(self, ctx: AppContext, paper_id: int, windows, parent=None) -> None:
        super().__init__(parent)
        self.ctx, self.paper_id, self.windows = ctx, paper_id, windows
        lay = QVBoxLayout(self)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["种类", "子类型", "文件名", "添加时间"])
        self.tree.setRootIsDecorated(False)
        self.tree.setColumnWidth(0, 90)
        self.tree.setColumnWidth(1, 90)
        self.tree.setColumnWidth(2, 380)
        self.tree.itemDoubleClicked.connect(lambda *_: self.open_selected())
        lay.addWidget(self.tree)
        add_buttons(lay, [("打开（阅读器）", self.open_selected), ("用系统程序打开", self.open_external),
                          ("添加文件…", self.add_files), ("设置 PDF 子类型…", self.set_subtype),
                          ("移除", self.remove_selected)])
        self.refresh()

    def refresh(self) -> None:
        self.tree.clear()
        order = {KIND_PDF: 0, KIND_TRANSLATION: 1, KIND_CARD: 2, KIND_ATTACHMENT: 3}
        files = sorted(self.ctx.files.list(self.paper_id), key=lambda f: (order[f.kind], f.id))
        for f in files:
            it = QTreeWidgetItem([KIND_LABELS[f.kind], f.subtype, f.display_name, f.added_at])
            it.setData(0, Qt.UserRole, f.id)
            self.tree.addTopLevelItem(it)

    def _selected_file(self):
        it = self.tree.currentItem()
        if not it:
            return None
        return next((f for f in self.ctx.files.list(self.paper_id)
                     if f.id == it.data(0, Qt.UserRole)), None)

    @guarded
    def open_selected(self) -> None:
        f = self._selected_file()
        if not f:
            return
        if f.kind in (KIND_PDF, KIND_TRANSLATION):
            self.windows.open_reader(self.paper_id, file_id=f.id)
        else:
            open_path(self.ctx.files.abs_path(f))

    @guarded
    def open_external(self) -> None:
        f = self._selected_file()
        if f:
            open_path(self.ctx.files.abs_path(f))

    @guarded
    def add_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "添加文件到这篇论文")
        for p in paths:
            info = classify(Path(p))
            self.ctx.files.add(self.paper_id, info.kind, p, subtype=info.subtype)

    @guarded
    def set_subtype(self) -> None:
        f = self._selected_file()
        if not f or f.kind != KIND_PDF:
            return
        options = [SUBTYPE_MAIN, SUBTYPE_SUPPLEMENT, SUBTYPE_APPENDIX, "其他"]
        cur = options.index(f.subtype) if f.subtype in options else 0
        val, ok = QInputDialog.getItem(self, "PDF 子类型", "类型：", options, cur, True)
        if ok:
            self.ctx.files.set_subtype(f.id, val.strip())

    @guarded
    def remove_selected(self) -> None:
        f = self._selected_file()
        if f and QMessageBox.question(
                self, "移除文件", f"从文献库移除并删除库内副本？\n{f.display_name}\n（你原来的源文件不受影响）"
        ) == QMessageBox.Yes:
            self.ctx.files.remove(f.id)
