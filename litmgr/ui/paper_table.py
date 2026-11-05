"""论文列表（表格）。

【作用】以表格显示检索结果：标题、阅读状态、星级、你选择显示的字段列、标签。
【职责】
    - PaperTableModel：把 Paper 列表适配成 Qt 表格模型；列由“字段是否在列表显示”决定
    - PaperTable：表格控件，支持多选、双击打开、点击表头排序、
      右键表头选择显示哪些字段列、右键行弹出论文操作菜单（由外部提供菜单内容）
【依赖】PySide6；core.models；services（通过 AppContext）。
【被谁调用】ui.main_window。
"""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QMenu, QTableView

from ..core.models import READ_STATUS, ROLE_TITLE, Paper
from ..services.app_context import AppContext

STATUS_COLORS = {"unread": "#888888", "reading": "#d9822b", "read": "#2e8b57", "deep": "#1f6fd1"}
# 预先创建好颜色对象：data() 每次重绘都会被大量调用，不必每次新建
_STATUS_BRUSHES = {k: QColor(v) for k, v in STATUS_COLORS.items()}
_BLACK = QColor("#000")
_RATING_COLOR = QColor("#e0a800")


class PaperTableModel(QAbstractTableModel):
    def __init__(self, ctx: AppContext) -> None:
        super().__init__()
        self.ctx = ctx
        self.papers: list[Paper] = []
        self.columns: list[tuple[str, str]] = []   # (key, 表头)
        self.tag_map: dict[int, list[str]] = {}
        self.reload_columns()

    def reload_columns(self) -> None:
        """根据字段定义重建列：标题 | 状态 | 星级 | 勾选显示的字段 | 标签。"""
        self.beginResetModel()
        cols = [("title", "标题"), ("status", "状态"), ("rating", "星级")]
        for f in self.ctx.fields.list():
            if f.show_in_list and f.role != ROLE_TITLE:
                cols.append((f"f:{f.id}", f.name))
        cols.append(("tags", "标签"))
        self.columns = cols
        self.endResetModel()

    def set_papers(self, papers: list[Paper]) -> None:
        self.beginResetModel()
        self.papers = papers
        self.tag_map = self.ctx.organize.tag_map()
        self.endResetModel()

    def paper_at(self, row: int) -> Paper | None:
        return self.papers[row] if 0 <= row < len(self.papers) else None

    # ---------- Qt 模型接口 ----------
    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.papers)

    def columnCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.columns)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.columns[section][1]
        return None

    def _text(self, p: Paper, key: str) -> str:
        if key == "title":
            return p.title
        if key == "status":
            return READ_STATUS.get(p.read_status, p.read_status)
        if key == "rating":
            return "★" * p.rating + "☆" * (5 - p.rating) if p.rating else ""
        if key == "tags":
            return "、".join(self.tag_map.get(p.id, []))
        if key.startswith("f:"):
            return p.text_of(int(key[2:]))
        return ""

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        p, key = self.papers[index.row()], self.columns[index.column()][0]
        if role == Qt.DisplayRole:
            return self._text(p, key)[:200].replace("\n", " ")    # 先截断再替换：长文本不必整段处理
        if role == Qt.ToolTipRole:
            return self._text(p, key)[:1500] or None
        if role == Qt.ForegroundRole and key == "status":
            return _STATUS_BRUSHES.get(p.read_status, _BLACK)
        if role == Qt.ForegroundRole and key == "rating":
            return _RATING_COLOR
        return None


class PaperTable(QTableView):
    openRequested = Signal(int)          # 双击/回车：打开论文详情
    selectionIdsChanged = Signal(list)   # 选中的论文 id 列表
    sortRequested = Signal(str, bool)    # (列 key, 是否降序)
    columnsToggled = Signal(int, bool)   # (字段 id, 是否显示)

    def __init__(self, ctx: AppContext, parent=None) -> None:
        super().__init__(parent)
        self.ctx = ctx
        self.model_ = PaperTableModel(ctx)
        self.setModel(self.model_)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setAlternatingRowColors(True)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setWordWrap(False)
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(28)
        hh = self.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.Interactive)
        hh.setStretchLastSection(True)
        hh.setSectionsClickable(True)
        hh.setContextMenuPolicy(Qt.CustomContextMenu)
        hh.customContextMenuRequested.connect(self._header_menu)
        hh.sectionClicked.connect(self._on_header_clicked)
        self.doubleClicked.connect(lambda idx: self._open(idx.row()))
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._row_menu)
        self.menu_builder: Callable[[QMenu, list[int]], None] | None = None
        self._sort_key, self._sort_desc = "id", True
        self.selectionModel().selectionChanged.connect(lambda *_: self._emit_selection())
        self._apply_widths()

    # ---------- 数据 ----------
    def set_papers(self, papers: list[Paper], keep_selection: bool = True) -> None:
        keep = set(self.selected_ids()) if keep_selection else set()
        self.model_.set_papers(papers)
        if keep:
            sm = self.selectionModel()
            sm.blockSignals(True)     # 逐行恢复选中时不要每行都通知一次，最后统一通知
            try:
                for row, p in enumerate(papers):
                    if p.id in keep:
                        sm.select(self.model_.index(row, 0),
                                  sm.SelectionFlag.Select | sm.SelectionFlag.Rows)
            finally:
                sm.blockSignals(False)
        self._emit_selection()   # 模型重置不会触发 selectionChanged，这里手动通知

    def reload_columns(self) -> None:
        """字段定义变化后重建列（只在此时重置列宽，普通检索刷新不会打乱你拖好的列宽）。"""
        self.model_.reload_columns()
        self._apply_widths()

    def selected_ids(self) -> list[int]:
        rows = sorted({i.row() for i in self.selectionModel().selectedRows()}) \
            if self.selectionModel() else []
        return [self.model_.papers[r].id for r in rows if r < len(self.model_.papers)]

    def paper_count(self) -> int:
        return len(self.model_.papers)

    def _emit_selection(self) -> None:
        self.selectionIdsChanged.emit(self.selected_ids())

    def _apply_widths(self) -> None:
        for i, (key, _h) in enumerate(self.model_.columns):
            self.setColumnWidth(i, {"title": 380, "status": 60, "rating": 80, "tags": 160}.get(key, 150))

    def _open(self, row: int) -> None:
        p = self.model_.paper_at(row)
        if p:
            self.openRequested.emit(p.id)

    def keyPressEvent(self, e) -> None:
        if e.key() in (Qt.Key_Return, Qt.Key_Enter) and self.currentIndex().isValid():
            self._open(self.currentIndex().row())
            return
        super().keyPressEvent(e)

    # ---------- 排序 ----------
    def _on_header_clicked(self, section: int) -> None:
        key = self.model_.columns[section][0]
        if key == "tags":
            return
        self._sort_desc = (not self._sort_desc) if key == self._sort_key else False
        self._sort_key = key
        self.sortRequested.emit(key, self._sort_desc)
        self.horizontalHeader().setSortIndicator(
            section, Qt.DescendingOrder if self._sort_desc else Qt.AscendingOrder)
        self.horizontalHeader().setSortIndicatorShown(True)

    # ---------- 菜单 ----------
    def _header_menu(self, pos) -> None:
        menu = QMenu(self)
        menu.addSection("显示哪些字段列")
        for f in self.ctx.fields.list():
            if f.role == ROLE_TITLE:
                continue
            act = menu.addAction(f.name)
            act.setCheckable(True)
            act.setChecked(f.show_in_list)
            act.toggled.connect(lambda on, fid=f.id: self.columnsToggled.emit(fid, on))
        menu.exec(self.horizontalHeader().mapToGlobal(pos))

    def _row_menu(self, pos) -> None:
        idx = self.indexAt(pos)
        if idx.isValid() and not self.selectionModel().isRowSelected(idx.row(), QModelIndex()):
            self.selectRow(idx.row())
        ids = self.selected_ids()
        if not ids or self.menu_builder is None:
            return
        menu = QMenu(self)
        self.menu_builder(menu, ids)
        menu.exec(self.viewport().mapToGlobal(pos))
