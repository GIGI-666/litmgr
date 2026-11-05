"""“最近阅读”菜单。

【作用】维护主窗口的“最近阅读”下拉菜单：列出最近阅读的论文，点击即打开阅读窗口并还原
    关闭时的页面状态；末尾有“清空阅读历史”。
【同步】订阅阅读历史/论文标题/论文删除/批量导入事件，自动重建菜单。
【依赖】services.reading_history_service（经 AppContext）；ui.utils。
【被谁调用】ui.main_window（文件菜单与工具栏共用同一个菜单对象 self.menu）。
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QTimer
from PySide6.QtWidgets import QMenu, QToolButton, QWidget

from ..core.events import Events
from ..services.app_context import AppContext
from .utils import EventSubscriberMixin, guarded


class RecentReadingMenu(EventSubscriberMixin, QObject):
    def __init__(self, widget: QWidget, ctx: AppContext, windows) -> None:
        super().__init__(widget)
        self.widget = widget          # 弹窗的父窗口（guarded 会用到）
        self.ctx, self.windows = ctx, windows
        self.menu = QMenu("最近阅读(&R)", widget)
        self.rebuild()
        # 论文标题变化/论文删除/批量导入时，菜单里的标题也要更新
        for ev in (Events.READING_HISTORY_CHANGED, Events.PAPER_CHANGED, Events.PAPER_DELETED,
                   Events.LIBRARY_CHANGED):
            self.subscribe(ctx.events, ev, self._schedule_rebuild)

    def make_tool_button(self) -> QToolButton:
        """工具栏上的下拉按钮（与文件菜单共用同一个菜单）。"""
        btn = QToolButton()
        btn.setText("最近阅读 ▾")
        btn.setToolTip("最近阅读的 10 篇论文；点击即可还原到关闭时的页面")
        btn.setPopupMode(QToolButton.InstantPopup)
        btn.setMenu(self.menu)
        return btn

    def dispose(self) -> None:
        self.unsubscribe_all()

    def _schedule_rebuild(self, **_kw) -> None:
        # 延后到当前事件处理结束：避免在菜单项自己的点击回调里把它删掉
        QTimer.singleShot(0, self, self.rebuild)

    def rebuild(self) -> None:
        """按阅读历史重建菜单（创建时调用一次，之后由事件触发）。"""
        m = self.menu
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
