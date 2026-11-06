"""主窗口：论文库总览。

【作用】文献管理的“主界面”：把导航、搜索栏、论文列表、预览四块拼在一起并协调它们。
    所有其他窗口（详情、阅读、对比、导入向导、字段管理）都从这里打开。
【拆分】本文件只负责“装配与协调”，具体功能在：
    ui.nav_panel（左侧导航）/ ui.paper_table（列表）/ ui.preview_panel（右侧预览）/
    ui.paper_actions（右键菜单与批量操作、导出）/ ui.recent_menu（最近阅读菜单）。
【布局】
    工具栏：导入 | 新建 | 字段管理 | 阅读 | 对比 | 新主窗口 | 最近阅读（下拉，最近 10 篇，点击还原页面）
    搜索栏：关键词 + 搜索范围 + 高级过滤 + 保存检索
    侧栏  ：导航树（右键可新建/重命名/删除分组与标签）
    列表  ：点表头排序；右键表头选列；右键行有完整论文操作菜单
【同步】订阅事件总线（论文/字段/整理/文件变化），合并短时间内的多次变化后统一刷新。
【依赖】上述面板模块；filter_dialog / field_manager_dialog / backup_dialog / window_manager；
    services（通过 AppContext）；core.config（保存窗口位置）。
【被谁调用】litmgr.__main__ 启动；WindowManager.main_window。
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QByteArray, QProcess, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (QApplication, QComboBox, QFileDialog, QHBoxLayout, QInputDialog,
                               QLabel, QLineEdit, QMainWindow, QMessageBox, QSplitter,
                               QToolBar, QVBoxLayout, QWidget)

from .. import APP_NAME, __version__
from ..core.config import AppConfig
from ..core.events import Events
from ..core.query import SearchQuery
from ..services.app_context import AppContext
from .backup_dialog import BackupDialog
from .field_manager_dialog import FieldManagerDialog
from .filter_dialog import FilterDialog
from .nav_panel import NavPanel
from .paper_actions import PaperActions
from .paper_table import PaperTable
from .preview_panel import PreviewPanel
from .recent_menu import RecentReadingMenu
from .utils import EventSubscriberMixin, guarded, make_button

STATE_KEY = "main_window"      # 在 AppConfig.ui_state 里存放本窗口状态的键


class MainWindow(EventSubscriberMixin, QMainWindow):
    closed = Signal()

    def __init__(self, ctx: AppContext, windows, config: AppConfig | None = None) -> None:
        super().__init__()
        self.ctx, self.windows, self.config = ctx, windows, config
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowTitle(f"{APP_NAME} - {ctx.library_path}")
        self.resize(1500, 900)
        self.query = SearchQuery()
        self.actions_ = PaperActions(self, ctx, windows)
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
        self.subscribe(bus, Events.LIST_COLUMNS_CHANGED, self._on_list_columns_changed)

        self._restore_state()
        self.nav.reload()
        self.refresh()

    @property
    def nav_tuple(self) -> tuple:
        """当前侧栏选中项（导航元组），以导航面板为准。"""
        return self.nav.current_nav

    # ================= 构建界面 =================
    def _build_actions(self) -> None:
        def act(text, slot, shortcut=None, tip=""):
            a = QAction(text, self)
            a.triggered.connect(lambda _=False: slot())
            if shortcut:
                a.setShortcut(QKeySequence(shortcut))
            a.setToolTip(tip or text)
            return a

        pa = self.actions_
        self.a_import = act("导入论文…", self.windows.open_import_wizard, "Ctrl+I",
                            "导入论文卡片 / PDF / 翻译")
        self.a_new = act("新建空白论文", pa.new_blank, "Ctrl+N")
        self.a_fields = act("字段管理…", self.open_field_manager, "Ctrl+Shift+F")
        self.a_read = act("阅读选中论文", lambda: pa.read(self.table.selected_ids()), "Ctrl+R",
                          "PDF 与翻译并排阅读")
        self.a_compare = act("对比选中论文", lambda: pa.compare(self.table.selected_ids()),
                             "Ctrl+M")
        self.a_new_main = act("新建主窗口", lambda: self.windows.open_main(self.config),
                              "Ctrl+Shift+N")
        self.a_undo = act("撤销上一次字段修改", self.undo_last, "Ctrl+Z")
        self.a_backup = act("备份与恢复…", self.open_backup)
        self.a_switch = act("切换文献库…", self.switch_library)
        self.a_export_all = act("导出全部论文为 CSV…", pa.export_all_csv)
        self.a_reindex = act("重建全文索引", self.reindex)
        self.a_about = act("关于", self.about)
        self.a_quit = act("退出", QApplication.instance().closeAllWindows, "Ctrl+Q")

        # “最近阅读”菜单：文件菜单与工具栏共用同一个菜单对象
        self.recent = RecentReadingMenu(self, self.ctx, self.windows)
        self.recent_menu = self.recent.menu

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
        tb.addWidget(self.recent.make_tool_button())

    def _build_ui(self) -> None:
        split = QSplitter(Qt.Horizontal)
        self.setCentralWidget(split)

        # 左：导航
        self.nav = NavPanel(self.ctx)
        self.nav.navChanged.connect(self._on_nav_changed)
        split.addWidget(self.nav)

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
        self.scope_box.currentIndexChanged.connect(lambda _i: self._apply_search_inputs())
        self.filter_btn = make_button("高级过滤…", self.open_filter)
        self.clear_btn = make_button("清除", self.clear_search)
        self.save_view_btn = make_button("保存检索…", self.save_view)
        bar.addWidget(self.search_edit, 1)
        bar.addWidget(QLabel("范围："))
        bar.addWidget(self.scope_box)
        for b in (self.filter_btn, self.clear_btn, self.save_view_btn):
            bar.addWidget(b)
        ml.addLayout(bar)
        self.table = PaperTable(self.ctx)
        self.table.menu_builder = self.actions_.build_row_menu
        self.table.openRequested.connect(lambda pid: self.windows.open_detail(pid))
        self.table.selectionIdsChanged.connect(self._on_selection)
        self.table.sortRequested.connect(self._on_sort)
        self.table.columnsToggled.connect(self._on_column_toggled)
        ml.addWidget(self.table, 1)
        split.addWidget(mid)

        # 右：预览
        self.preview = PreviewPanel(self.ctx)
        self.preview.openRequested.connect(self._open_current)
        self.preview.readRequested.connect(lambda: self.actions_.read(self.table.selected_ids()))
        split.addWidget(self.preview)
        split.setSizes([210, 900, 380])
        self.split = split

        self.count_label = QLabel()
        self.statusBar().addPermanentWidget(self.count_label)
        self.statusBar().showMessage(f"文献库：{self.ctx.library_path}")
        self._reload_scope_box()
        self._on_selection([])

    # ================= 导航 =================
    def _on_nav_changed(self, data: tuple) -> None:
        if data[0] == "view":    # 选中“保存的检索”：载入它的搜索条件
            view = next((v for v in self.ctx.organize.views() if v.id == data[1]), None)
            if view:
                self.query = SearchQuery.from_dict(view.query)
                self._sync_inputs_from_query()
        self.refresh()

    def _on_organize_changed(self, **_kw) -> None:
        self.nav.reload()
        self._schedule_refresh()

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
        self.nav.select_all()      # 触发 navChanged -> refresh

    @guarded
    def open_filter(self) -> None:
        dlg = FilterDialog(self, self.ctx, self.query, lock_status=self.nav_tuple[0] == "status")
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
        q = self.query.copy()
        nav = self.nav_tuple
        if nav[0] == "status":
            q.read_status = nav[1]
        elif nav[0] == "collection":
            q.collection_id = nav[1]
        elif nav[0] == "tag":
            q.tag_ids = list(q.tag_ids) + [nav[1]]
        return q

    def _on_sort(self, key: str, desc: bool) -> None:
        self.query.sort_key, self.query.sort_desc = key, desc
        self.refresh()

    @guarded
    def _on_column_toggled(self, field_id: int, on: bool) -> None:
        self.ctx.fields.set_show_in_list(field_id, on)

    # ================= 刷新 =================
    def _schedule_refresh(self, **_kw) -> None:
        self._refresh_timer.start()

    def _on_fields_changed(self, **_kw) -> None:
        self._reload_scope_box()
        self.table.reload_columns()
        self._schedule_refresh()

    def _on_list_columns_changed(self, **_kw) -> None:
        self.table.reload_columns()
        self._schedule_refresh()

    @guarded
    def refresh(self) -> None:
        papers = self.ctx.search.run(self._effective_query())
        self.table.set_papers(papers)
        total = self.ctx.papers.count()
        self.count_label.setText(f"显示 {len(papers)} / 共 {total} 篇")
        status_in_filter = bool(self.query.read_status) and self.nav_tuple[0] != "status"   # 侧栏选了状态时，这里的状态不生效
        n_cond = len(self.query.conditions) + status_in_filter + bool(self.query.min_rating)
        self.filter_btn.setText(f"高级过滤…（{n_cond}）" if n_cond else "高级过滤…")
        # 选中项的预览/按钮状态已由 table.set_papers 发出的 selectionIdsChanged 更新，这里不必重复

    # ================= 选中与预览 =================
    def _on_selection(self, ids: list[int]) -> None:
        has = bool(ids)
        for a in (self.a_read, self.a_compare):
            a.setEnabled(has)
        self.preview.show_selection(ids)

    def _open_current(self) -> None:
        ids = self.table.selected_ids()
        if len(ids) == 1:
            self.windows.open_detail(ids[0])

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

    # ================= 窗口状态（保存在 AppConfig.ui_state，不再用系统注册表） =================
    def _restore_state(self) -> None:
        if self.config is None:
            return
        st = self.config.ui_state.get(STATE_KEY, {})
        if geo := st.get("geometry"):
            self.restoreGeometry(QByteArray.fromBase64(geo.encode("ascii")))
        if sizes := st.get("split"):
            self.split.setSizes([int(x) for x in sizes])

    def _save_state(self) -> None:
        if self.config is None:
            return
        self.config.ui_state[STATE_KEY] = {
            "geometry": bytes(self.saveGeometry().toBase64()).decode("ascii"),
            "split": self.split.sizes(),
        }
        self.config.save()

    def closeEvent(self, e) -> None:
        self._save_state()
        self.recent.dispose()
        self.unsubscribe_all()
        self.closed.emit()
        super().closeEvent(e)
