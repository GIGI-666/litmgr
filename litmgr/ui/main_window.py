"""主窗口：论文库总览。

【作用】文献管理的“主界面”：左侧导航（全部/阅读状态/分组/标签/保存的检索），
    中间搜索栏 + 论文列表，右侧所选论文的快速预览。
    所有其他窗口（详情、阅读、对比、导入向导、字段管理）都从这里打开。
【布局】
    工具栏：导入 | 新建 | 字段管理 | 阅读 | 对比 | 新主窗口 | 最近阅读（下拉，最近 10 篇，点击还原页面）
    搜索栏：关键词 + 搜索范围 + 高级过滤 + 保存检索
    侧栏  ：导航树（右键可新建/重命名/删除分组与标签）
    列表  ：点表头排序；右键表头选列；右键行有完整论文操作菜单
【同步】订阅事件总线（论文/字段/整理/文件变化），合并短时间内的多次变化后统一刷新。
【依赖】ui.paper_table / filter_dialog / field_manager_dialog / backup_dialog /
    organize_panel / window_manager；services（通过 AppContext）。
【被谁调用】litmgr.__main__ 启动；WindowManager.main_window。
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QProcess, QSettings, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (QApplication, QComboBox, QFileDialog, QHBoxLayout, QInputDialog,
                               QLabel, QLineEdit, QMainWindow, QMenu, QMessageBox, QPushButton,
                               QSplitter, QTextBrowser, QToolBar, QToolButton, QTreeWidget, QTreeWidgetItem,
                               QVBoxLayout, QWidget)

from .. import APP_NAME, __version__
from ..core.config import AppConfig
from ..core.events import Events
from ..core.models import KIND_LABELS, READ_STATUS
from ..services.app_context import AppContext
from ..services.search_service import SearchQuery
from .backup_dialog import BackupDialog
from .field_manager_dialog import FieldManagerDialog
from .filter_dialog import FilterDialog
from .organize_panel import edit_collections_for, edit_tags_for
from .paper_table import PaperTable
from .utils import EventSubscriberMixin, guarded

# 侧栏节点的数据角色
ROLE_NAV = Qt.UserRole


class MainWindow(EventSubscriberMixin, QMainWindow):
    closed = Signal()

    def __init__(self, ctx: AppContext, windows, config: AppConfig | None = None) -> None:
        super().__init__()
        self.ctx, self.windows, self.config = ctx, windows, config
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowTitle(f"{APP_NAME} - {ctx.library_path}")
        self.resize(1500, 900)
        self.query = SearchQuery()
        self.nav: tuple = ("all",)
        self._building_ui = True

        self._build_actions()
        self._build_ui()
        self._building_ui = False

        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.setInterval(60)
        self._refresh_timer.timeout.connect(self.refresh)
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(250)
        self._search_timer.timeout.connect(self._apply_search_inputs)

        bus = ctx.events
        for ev in (Events.PAPER_ADDED, Events.PAPER_CHANGED, Events.PAPER_DELETED,
                   Events.FILES_CHANGED, Events.LIBRARY_CHANGED, Events.NOTES_CHANGED):
            self.subscribe(bus, ev, self._schedule_refresh)
        self.subscribe(bus, Events.ORGANIZE_CHANGED, self._on_organize_changed)
        self.subscribe(bus, Events.FIELDS_CHANGED, self._on_fields_changed)
        # 论文标题变化/论文删除/批量导入时，菜单里的标题也要更新
        for ev in (Events.READING_HISTORY_CHANGED, Events.PAPER_CHANGED, Events.PAPER_DELETED,
                   Events.LIBRARY_CHANGED):
            self.subscribe(bus, ev, self._schedule_recent_rebuild)

        self._restore_geometry()
        self.reload_nav()
        self.refresh()

    # ================= 构建界面 =================
    def _build_actions(self) -> None:
        def act(text, slot, shortcut=None, tip=""):
            a = QAction(text, self)
            a.triggered.connect(lambda _=False: slot())
            if shortcut:
                a.setShortcut(QKeySequence(shortcut))
            a.setToolTip(tip or text)
            return a

        self.a_import = act("导入论文…", self.windows.open_import_wizard, "Ctrl+I",
                            "导入论文卡片 / PDF / 翻译")
        self.a_new = act("新建空白论文", self.new_blank, "Ctrl+N")
        self.a_fields = act("字段管理…", self.open_field_manager, "Ctrl+Shift+F")
        self.a_read = act("阅读选中论文", self.read_selected, "Ctrl+R", "PDF 与翻译并排阅读")
        self.a_compare = act("对比选中论文", self.compare_selected, "Ctrl+M")
        self.a_new_main = act("新建主窗口", self.new_main_window, "Ctrl+Shift+N")
        self.a_undo = act("撤销上一次字段修改", self.undo_last, "Ctrl+Z")
        self.a_backup = act("备份与恢复…", self.open_backup)
        self.a_switch = act("切换文献库…", self.switch_library)
        self.a_export_all = act("导出全部论文为 CSV…", self.export_all_csv)
        self.a_reindex = act("重建全文索引", self.reindex)
        self.a_about = act("关于", self.about)
        self.a_quit = act("退出", QApplication.instance().closeAllWindows, "Ctrl+Q")

        # “最近阅读”菜单：文件菜单与工具栏共用同一个菜单对象
        self.recent_menu = QMenu("最近阅读(&R)", self)
        self.rebuild_recent_menu()

        mb = self.menuBar()
        m = mb.addMenu("文件(&F)")
        m.addMenu(self.recent_menu)
        m.addSeparator()
        for a in (self.a_import, self.a_new, self.a_new_main, None, self.a_export_all,
                  self.a_backup, self.a_switch, None, self.a_quit):
            m.addSeparator() if a is None else m.addAction(a)
        m = mb.addMenu("编辑(&E)")
        m.addAction(self.a_undo)
        m = mb.addMenu("工具(&T)")
        m.addAction(self.a_fields)
        m.addAction(self.a_reindex)
        m = mb.addMenu("帮助(&H)")
        m.addAction(self.a_about)

        tb = QToolBar("工具栏")
        tb.setMovable(False)
        self.addToolBar(tb)
        for a in (self.a_import, self.a_new, self.a_fields, self.a_read, self.a_compare,
                  self.a_new_main):
            tb.addAction(a)
        recent_btn = QToolButton()
        recent_btn.setText("最近阅读 ▾")
        recent_btn.setToolTip("最近阅读的 10 篇论文；点击即可还原到关闭时的页面")
        recent_btn.setPopupMode(QToolButton.InstantPopup)
        recent_btn.setMenu(self.recent_menu)
        tb.addWidget(recent_btn)

    # ---------- 最近阅读 ----------
    def _schedule_recent_rebuild(self, **_kw) -> None:
        # 延后到当前事件处理结束：避免在菜单项自己的点击回调里把它删掉
        QTimer.singleShot(0, self, self.rebuild_recent_menu)

    def rebuild_recent_menu(self) -> None:
        """按阅读历史重建“最近阅读”菜单（启动时调用一次，之后由事件触发）。"""
        m = self.recent_menu
        m.clear()
        items = self.ctx.reading.recent()
        if not items:
            m.addAction("（还没有阅读记录）").setEnabled(False)
        for i, it in enumerate(items, 1):
            title = it.title if len(it.title) <= 48 else it.title[:47] + "…"
            a = m.addAction(f"{i}. {title}    ({it.last_opened[5:16]})")
            a.setToolTip(it.title)
            a.triggered.connect(lambda _=False, pid=it.paper_id: self.open_from_history(pid))
        m.addSeparator()
        clear = m.addAction("清空阅读历史")
        clear.setEnabled(bool(items))
        clear.triggered.connect(lambda _=False: self.ctx.reading.clear())

    @guarded
    def open_from_history(self, paper_id: int) -> None:
        """从历史记录打开阅读窗口，并还原关闭时的页面状态。"""
        self.windows.open_reader(paper_id, restore=True)

    def _build_ui(self) -> None:
        split = QSplitter(Qt.Horizontal)
        self.setCentralWidget(split)

        # 左：导航
        self.nav_tree = QTreeWidget()
        self.nav_tree.setHeaderHidden(True)
        self.nav_tree.setMinimumWidth(190)
        self.nav_tree.itemSelectionChanged.connect(self._on_nav_changed)
        self.nav_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.nav_tree.customContextMenuRequested.connect(self._nav_menu)
        split.addWidget(self.nav_tree)

        # 中：搜索 + 列表
        mid = QWidget()
        ml = QVBoxLayout(mid)
        ml.setContentsMargins(0, 0, 0, 0)
        bar = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索：多个词用空格分隔（全部命中）；支持字段、翻译正文、笔记")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(lambda _t: self._search_timer.start())
        self.scope_box = QComboBox()
        self.scope_box.currentIndexChanged.connect(lambda _i: self._on_scope_changed())
        self.filter_btn = QPushButton("高级过滤…")
        self.filter_btn.clicked.connect(self.open_filter)
        self.clear_btn = QPushButton("清除")
        self.clear_btn.clicked.connect(self.clear_search)
        self.save_view_btn = QPushButton("保存检索…")
        self.save_view_btn.clicked.connect(self.save_view)
        bar.addWidget(self.search_edit, 1)
        bar.addWidget(QLabel("范围："))
        bar.addWidget(self.scope_box)
        for b in (self.filter_btn, self.clear_btn, self.save_view_btn):
            bar.addWidget(b)
        ml.addLayout(bar)
        self.table = PaperTable(self.ctx)
        self.table.menu_builder = self._build_row_menu
        self.table.openRequested.connect(lambda pid: self.windows.open_detail(pid))
        self.table.selectionIdsChanged.connect(self._on_selection)
        self.table.sortRequested.connect(self._on_sort)
        self.table.columnsToggled.connect(self._on_column_toggled)
        ml.addWidget(self.table, 1)
        split.addWidget(mid)

        # 右：预览
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        self.preview = QTextBrowser()
        self.preview.setOpenExternalLinks(True)
        rl.addWidget(self.preview, 1)
        brow = QHBoxLayout()
        self.open_btn, self.read_btn = QPushButton("打开详情"), QPushButton("阅读")
        self.open_btn.clicked.connect(self._open_current)
        self.read_btn.clicked.connect(self.read_selected)
        brow.addWidget(self.open_btn)
        brow.addWidget(self.read_btn)
        rl.addLayout(brow)
        split.addWidget(right)
        split.setSizes([210, 900, 380])
        self.split = split

        self.count_label = QLabel()
        self.statusBar().addPermanentWidget(self.count_label)
        self.statusBar().showMessage(f"文献库：{self.ctx.library_path}")
        self._reload_scope_box()
        self._on_selection([])

    # ================= 导航树 =================
    def reload_nav(self) -> None:
        """重建左侧导航，并尽量保持原来的选中项。"""
        self.nav_tree.blockSignals(True)
        self.nav_tree.clear()

        def node(parent, text, data):
            it = QTreeWidgetItem(parent if parent is not None else self.nav_tree, [text])
            it.setData(0, ROLE_NAV, data)
            return it

        self._nav_items = {}
        self._nav_items[("all",)] = node(None, "全部论文", ("all",))
        status = node(None, "阅读状态", ("group",))
        for k, v in READ_STATUS.items():
            self._nav_items[("status", k)] = node(status, v, ("status", k))
        cols = node(None, "分组", ("group", "collections"))
        counts = self.ctx.organize.collection_counts()
        for c in self.ctx.organize.collections():
            self._nav_items[("collection", c.id)] = node(
                cols, f"{c.name} ({counts.get(c.id, 0)})", ("collection", c.id))
        tags = node(None, "标签", ("group", "tags"))
        tcounts = self.ctx.organize.tag_counts()
        for t in self.ctx.organize.tags():
            self._nav_items[("tag", t.id)] = node(tags, f"{t.name} ({tcounts.get(t.id, 0)})",
                                                  ("tag", t.id))
        views = node(None, "保存的检索", ("group", "views"))
        for v in self.ctx.organize.views():
            self._nav_items[("view", v.id)] = node(views, v.name, ("view", v.id))
        self.nav_tree.expandAll()
        item = self._nav_items.get(self.nav) or self._nav_items[("all",)]
        self.nav_tree.setCurrentItem(item)
        self.nav_tree.blockSignals(False)

    def _on_nav_changed(self) -> None:
        it = self.nav_tree.currentItem()
        if not it:
            return
        data = it.data(0, ROLE_NAV)
        if data[0] == "group":
            return
        if data[0] == "view":
            view = next((v for v in self.ctx.organize.views() if v.id == data[1]), None)
            if view:
                self.query = SearchQuery.from_dict(view.query)
                self._sync_inputs_from_query()
            self.nav = data
        else:
            self.nav = data
        self.refresh()

    def _nav_menu(self, pos) -> None:
        it = self.nav_tree.itemAt(pos)
        menu = QMenu(self)
        data = it.data(0, ROLE_NAV) if it else None
        menu.addAction("新建分组…", self.new_collection)
        if data and data[0] == "collection":
            menu.addAction("重命名分组…", lambda: self.rename_nav(data))
            menu.addAction("删除分组", lambda: self.delete_nav(data))
        elif data and data[0] == "tag":
            menu.addAction("重命名标签…", lambda: self.rename_nav(data))
            menu.addAction("删除标签", lambda: self.delete_nav(data))
        elif data and data[0] == "view":
            menu.addAction("删除这个保存的检索", lambda: self.delete_nav(data))
        menu.exec(self.nav_tree.viewport().mapToGlobal(pos))

    @guarded
    def new_collection(self) -> None:
        name, ok = QInputDialog.getText(self, "新建分组", "分组名称：")
        if ok and name.strip():
            self.ctx.organize.add_collection(name)

    @guarded
    def rename_nav(self, data) -> None:
        kind, ident = data
        name, ok = QInputDialog.getText(self, "重命名", "新名称：")
        if ok and name.strip():
            if kind == "collection":
                self.ctx.organize.rename_collection(ident, name)
            else:
                self.ctx.organize.rename_tag(ident, name)

    @guarded
    def delete_nav(self, data) -> None:
        kind, ident = data
        label = {"collection": "分组", "tag": "标签", "view": "保存的检索"}[kind]
        if QMessageBox.question(self, "删除", f"确定删除这个{label}？\n（论文本身不会被删除）") \
                != QMessageBox.Yes:
            return
        if kind == "collection":
            self.ctx.organize.delete_collection(ident)
        elif kind == "tag":
            self.ctx.organize.delete_tag(ident)
        else:
            self.ctx.organize.delete_view(ident)
        if self.nav == data:
            self.nav = ("all",)

    # ================= 搜索 =================
    def _reload_scope_box(self) -> None:
        cur = self.scope_box.currentData() if self.scope_box.count() else ("all", True)
        self.scope_box.blockSignals(True)
        self.scope_box.clear()
        self.scope_box.addItem("全部内容（字段+翻译正文+笔记）", ("all", True))
        self.scope_box.addItem("仅卡片字段", ("all", False))
        for f in self.ctx.fields.list():
            self.scope_box.addItem(f"仅「{f.name}」", ("field", f.id))
        self.scope_box.setCurrentIndex(max(self.scope_box.findData(cur), 0))
        self.scope_box.blockSignals(False)

    def _on_scope_changed(self) -> None:
        self._apply_search_inputs()

    def _apply_search_inputs(self) -> None:
        """把搜索框与范围写入当前查询并刷新。"""
        if self._building_ui:
            return
        self.query.text = self.search_edit.text()
        kind, val = self.scope_box.currentData() or ("all", True)
        if kind == "field":
            self.query.scope_field_ids, self.query.include_fulltext = [val], False
        else:
            self.query.scope_field_ids, self.query.include_fulltext = None, val
        self.refresh()

    def _sync_inputs_from_query(self) -> None:
        """从查询对象反向设置搜索框与范围（选中“保存的检索”时）。"""
        q = self.query
        self.search_edit.blockSignals(True)
        self.scope_box.blockSignals(True)
        self.search_edit.setText(q.text)
        if q.scope_field_ids and len(q.scope_field_ids) == 1:
            data = ("field", q.scope_field_ids[0])
        else:
            data = ("all", q.include_fulltext)
        self.scope_box.setCurrentIndex(max(self.scope_box.findData(data), 0))
        self.search_edit.blockSignals(False)
        self.scope_box.blockSignals(False)

    def clear_search(self) -> None:
        sort_key, sort_desc = self.query.sort_key, self.query.sort_desc
        self.query = SearchQuery(sort_key=sort_key, sort_desc=sort_desc)
        self._sync_inputs_from_query()
        self.nav = ("all",)
        self.reload_nav()
        self.refresh()

    @guarded
    def open_filter(self) -> None:
        dlg = FilterDialog(self, self.ctx, self.query)
        if dlg.exec():
            dlg.apply_to(self.query)
            self.refresh()

    @guarded
    def save_view(self) -> None:
        name, ok = QInputDialog.getText(self, "保存检索", "给这个检索起个名字：")
        if ok and name.strip():
            self.ctx.organize.save_view(name, self._effective_query())

    def _effective_query(self) -> SearchQuery:
        """当前搜索框/过滤条件 + 侧栏选中项，合成最终查询。"""
        q = SearchQuery.from_dict(self.query.to_dict())
        kind = self.nav[0]
        if kind == "status":
            q.read_status = self.nav[1]
        elif kind == "collection":
            q.collection_id = self.nav[1]
        elif kind == "tag":
            q.tag_ids = list(q.tag_ids) + [self.nav[1]]
        return q

    def _on_sort(self, key: str, desc: bool) -> None:
        self.query.sort_key, self.query.sort_desc = key, desc
        self.refresh()

    @guarded
    def _on_column_toggled(self, field_id: int, on: bool) -> None:
        f = self.ctx.fields.get(field_id)
        f.show_in_list = on
        self.ctx.fields.update(f)

    # ================= 刷新 =================
    def _schedule_refresh(self, **_kw) -> None:
        self._refresh_timer.start()

    def _on_organize_changed(self, **_kw) -> None:
        self.reload_nav()
        self._schedule_refresh()

    def _on_fields_changed(self, **_kw) -> None:
        self._reload_scope_box()
        self.table.reload_columns()
        self._schedule_refresh()

    @guarded
    def refresh(self) -> None:
        papers = self.ctx.search.run(self._effective_query())
        self.table.set_papers(papers)
        total = self.ctx.papers.count()
        self.count_label.setText(f"显示 {len(papers)} / 共 {total} 篇")
        n_cond = len(self.query.conditions) + bool(self.query.read_status) + bool(self.query.min_rating)
        self.filter_btn.setText(f"高级过滤…（{n_cond}）" if n_cond else "高级过滤…")
        self._on_selection(self.table.selected_ids())

    # ================= 选中与预览 =================
    def _on_selection(self, ids: list[int]) -> None:
        has = bool(ids)
        for a in (self.a_read, self.a_compare):
            a.setEnabled(has)
        self.open_btn.setEnabled(len(ids) == 1)
        self.read_btn.setEnabled(has)
        if len(ids) == 1 and self.ctx.papers.exists(ids[0]):
            self.preview.setHtml(self._preview_html(ids[0]))
        elif len(ids) > 1:
            self.preview.setHtml(f"<p style='color:#666'>已选中 <b>{len(ids)}</b> 篇论文。<br>"
                                 "可右键批量操作，或点工具栏“对比选中论文”。</p>")
        else:
            self.preview.setHtml("<p style='color:#888'>选中一篇论文查看预览；双击或回车打开详情。</p>")

    def _preview_html(self, paper_id: int) -> str:
        import html as h
        p = self.ctx.papers.get(paper_id)
        tags = "、".join(t.name for t in self.ctx.organize.tags_of(paper_id)) or "无"
        cols = "、".join(c.name for c in self.ctx.organize.collections_of(paper_id)) or "无"
        parts = [f"<h3>{h.escape(p.title)}</h3>",
                 f"<p style='color:#666'>{READ_STATUS.get(p.read_status, '')}　"
                 f"{'★' * p.rating}{'☆' * (5 - p.rating)}<br>标签：{h.escape(tags)}　分组：{h.escape(cols)}</p>"]
        for f in self.ctx.fields.list():
            text = p.text_of(f.id).strip()
            if text:
                short = text if len(text) <= 260 else text[:260] + "…"
                parts.append(f"<p><b>{h.escape(f.name)}</b><br>{h.escape(short).replace(chr(10), '<br>')}</p>")
        files = self.ctx.papers.list_files(paper_id)
        if files:
            parts.append("<hr><p><b>文件</b><br>" + "<br>".join(
                f"[{KIND_LABELS[f.kind]}{('/' + f.subtype) if f.subtype else ''}] {h.escape(f.display_name)}"
                for f in files) + "</p>")
        return "".join(parts)

    def _single_selected(self) -> int | None:
        ids = self.table.selected_ids()
        return ids[0] if len(ids) == 1 else None

    # ================= 论文操作 =================
    def _open_current(self) -> None:
        pid = self._single_selected()
        if pid:
            self.windows.open_detail(pid)

    def read_selected(self) -> None:
        for pid in self.table.selected_ids()[:4]:   # 一次最多开 4 个，避免误操作
            self.windows.open_reader(pid)

    def compare_selected(self) -> None:
        ids = self.table.selected_ids()
        if ids:
            self.windows.open_compare(ids)

    @guarded
    def new_blank(self) -> None:
        pid = self.ctx.papers.create()
        self.windows.open_detail(pid)

    def new_main_window(self) -> None:
        self.windows.open_main(self.config)

    def _build_row_menu(self, menu: QMenu, ids: list[int]) -> None:
        single = len(ids) == 1
        if single:
            menu.addAction("打开详情", lambda: self.windows.open_detail(ids[0]))
            menu.addAction("在新窗口打开详情", lambda: self.windows.open_detail(ids[0], force_new=True))
        menu.addAction("阅读（PDF + 翻译）", self.read_selected)
        menu.addAction("对比选中的论文", self.compare_selected)
        menu.addSeparator()
        sm = menu.addMenu("设置阅读状态")
        for k, v in READ_STATUS.items():
            sm.addAction(v, lambda k=k: self._set_status(ids, k))
        rm = menu.addMenu("设置星级")
        for n in range(0, 6):
            rm.addAction("未评分" if n == 0 else "★" * n, lambda n=n: self._set_rating(ids, n))
        menu.addAction("加入分组…", lambda: edit_collections_for(self, self.ctx, ids))
        menu.addAction("打标签…", lambda: edit_tags_for(self, self.ctx, ids))
        menu.addSeparator()
        menu.addAction("导出选中为卡片 txt…", lambda: self._export_selected("txt", ids))
        menu.addAction("导出选中为 CSV…", lambda: self._export_selected("csv", ids))
        menu.addSeparator()
        menu.addAction("删除论文…", lambda: self._delete(ids))

    @guarded
    def _set_status(self, ids, status) -> None:
        for i in ids:
            self.ctx.papers.set_status(i, status)

    @guarded
    def _set_rating(self, ids, n) -> None:
        for i in ids:
            self.ctx.papers.set_rating(i, n)

    @guarded
    def _delete(self, ids) -> None:
        if QMessageBox.question(
                self, "删除论文",
                f"永久删除选中的 {len(ids)} 篇论文及其库内文件副本？\n此操作不可撤销（你的源文件不受影响）。"
        ) == QMessageBox.Yes:
            for i in ids:
                self.ctx.papers.delete(i)

    @guarded
    def _export_selected(self, fmt: str, ids) -> None:
        if fmt == "txt":
            d = QFileDialog.getExistingDirectory(self, "选择导出到的文件夹")
            if d:
                out = self.ctx.export.export("txt", ids, Path(d))
                QMessageBox.information(self, "导出完成", f"已导出 {len(out)} 个卡片文件。")
        else:
            path, _ = QFileDialog.getSaveFileName(self, "导出 CSV", "论文列表.csv", "CSV (*.csv)")
            if path:
                self.ctx.export.export("csv", ids, Path(path))

    @guarded
    def export_all_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "导出全部论文", "全部论文.csv", "CSV (*.csv)")
        if path:
            self.ctx.export.export("csv", [p.id for p in self.ctx.papers.list_all()], Path(path))

    # ================= 工具 =================
    @guarded
    def open_field_manager(self) -> None:
        FieldManagerDialog(self, self.ctx).exec()

    @guarded
    def open_backup(self) -> None:
        BackupDialog(self, self.ctx).exec()

    @guarded
    def undo_last(self) -> None:
        e = self.ctx.history.undo_last()
        self.statusBar().showMessage(
            f"已撤销：{e.field_name}" if e else "没有可撤销的修改", 4000)

    @guarded
    def reindex(self) -> None:
        self.ctx.papers.reindex_all()
        self.statusBar().showMessage("全文索引已重建", 4000)

    @guarded
    def switch_library(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "选择（或新建）文献库文件夹", str(self.ctx.library_path))
        if not d or Path(d) == self.ctx.library_path:
            return
        if self.config is not None:
            self.config.remember_library(d)
            self.config.save()
        QMessageBox.information(self, "切换文献库", "将重新启动程序以加载新的文献库。")
        QProcess.startDetached(sys.executable, ["-m", "litmgr"])
        QApplication.instance().closeAllWindows()

    def about(self) -> None:
        QMessageBox.about(self, "关于", f"{APP_NAME} v{__version__}\n本地单机、离线的个人文献管理系统。")

    # ================= 窗口状态 =================
    def _restore_geometry(self) -> None:
        s = QSettings("litmgr", "litmgr")
        geo, state = s.value("main/geometry"), s.value("main/split")
        if geo:
            self.restoreGeometry(geo)
        if state:
            self.split.restoreState(state)

    def closeEvent(self, e) -> None:
        s = QSettings("litmgr", "litmgr")
        s.setValue("main/geometry", self.saveGeometry())
        s.setValue("main/split", self.split.saveState())
        self.unsubscribe_all()
        self.closed.emit()
        super().closeEvent(e)
