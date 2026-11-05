"""左侧导航树。

【作用】主窗口左侧的导航：全部论文 / 阅读状态 / 分组 / 标签 / 保存的检索。
    选中某一项时发出 navChanged(导航元组)；右键可新建/重命名/删除分组与标签、删除保存的检索。
【导航元组】("all",) / ("status", 状态键) / ("collection", id) / ("tag", id) / ("view", id)。
    主窗口据此合成最终查询；“保存的检索”的具体查询由主窗口取出并应用。
【依赖】services.organize_service（经 AppContext）；ui.utils.guarded。
【被谁调用】ui.main_window。
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QInputDialog, QMenu, QMessageBox, QTreeWidget, QTreeWidgetItem

from ..core.models import READ_STATUS
from ..services.app_context import AppContext
from .utils import guarded

ALL = ("all",)


class NavPanel(QTreeWidget):
    navChanged = Signal(tuple)

    def __init__(self, ctx: AppContext, parent=None) -> None:
        super().__init__(parent)
        self.ctx = ctx
        self.current_nav: tuple = ALL
        self._items: dict[tuple, QTreeWidgetItem] = {}
        self.setHeaderHidden(True)
        self.setMinimumWidth(190)
        self.itemSelectionChanged.connect(self._on_selection_changed)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._menu)

    # ---------- 构建 ----------
    def reload(self) -> None:
        """重建导航树，并尽量保持原来的选中项（不触发 navChanged）。"""
        self.blockSignals(True)
        self.clear()
        self._items = {}

        def node(parent, text, data):
            it = QTreeWidgetItem(parent if parent is not None else self, [text])
            it.setData(0, Qt.UserRole, data)
            return it

        org = self.ctx.organize
        self._items[ALL] = node(None, "全部论文", ALL)
        status = node(None, "阅读状态", ("group",))
        for k, v in READ_STATUS.items():
            self._items[("status", k)] = node(status, v, ("status", k))
        cols = node(None, "分组", ("group", "collections"))
        counts = org.collection_counts()
        for c in org.collections():
            self._items[("collection", c.id)] = node(
                cols, f"{c.name} ({counts.get(c.id, 0)})", ("collection", c.id))
        tags = node(None, "标签", ("group", "tags"))
        tcounts = org.tag_counts()
        for t in org.tags():
            self._items[("tag", t.id)] = node(tags, f"{t.name} ({tcounts.get(t.id, 0)})",
                                              ("tag", t.id))
        views = node(None, "保存的检索", ("group", "views"))
        for v in org.views():
            self._items[("view", v.id)] = node(views, v.name, ("view", v.id))
        self.expandAll()
        self.setCurrentItem(self._items.get(self.current_nav) or self._items[ALL])
        self.blockSignals(False)

    def select_all(self) -> None:
        """回到“全部论文”并通知外界。"""
        self.current_nav = ALL
        self.reload()
        self.navChanged.emit(ALL)

    # ---------- 选中 ----------
    def _on_selection_changed(self) -> None:
        it = self.currentItem()
        if not it:
            return
        data = it.data(0, Qt.UserRole)
        if data[0] == "group":      # 点击分组标题本身不切换
            return
        self.current_nav = data
        self.navChanged.emit(data)

    # ---------- 右键菜单 ----------
    def _menu(self, pos) -> None:
        it = self.itemAt(pos)
        data = it.data(0, Qt.UserRole) if it else None
        menu = QMenu(self)
        menu.addAction("新建分组…", self.new_collection)
        if data and data[0] == "collection":
            menu.addAction("重命名分组…", lambda: self.rename(data))
            menu.addAction("删除分组", lambda: self.delete(data))
        elif data and data[0] == "tag":
            menu.addAction("重命名标签…", lambda: self.rename(data))
            menu.addAction("删除标签", lambda: self.delete(data))
        elif data and data[0] == "view":
            menu.addAction("删除这个保存的检索", lambda: self.delete(data))
        menu.exec(self.viewport().mapToGlobal(pos))

    @guarded
    def new_collection(self) -> None:
        name, ok = QInputDialog.getText(self, "新建分组", "分组名称：")
        if ok and name.strip():
            self.ctx.organize.add_collection(name)

    @guarded
    def rename(self, data) -> None:
        kind, ident = data
        name, ok = QInputDialog.getText(self, "重命名", "新名称：")
        if ok and name.strip():
            if kind == "collection":
                self.ctx.organize.rename_collection(ident, name)
            else:
                self.ctx.organize.rename_tag(ident, name)

    @guarded
    def delete(self, data) -> None:
        kind, ident = data
        label = {"collection": "分组", "tag": "标签", "view": "保存的检索"}[kind]
        if QMessageBox.question(self, "删除", f"确定删除这个{label}？\n（论文本身不会被删除）") \
                != QMessageBox.Yes:
            return
        if self.current_nav == data:
            self.current_nav = ALL      # 先切回“全部论文”，随后事件触发的刷新就不会再按已删除项查询
        if kind == "collection":
            self.ctx.organize.delete_collection(ident)
        elif kind == "tag":
            self.ctx.organize.delete_tag(ident)
        else:
            self.ctx.organize.delete_view(ident)
