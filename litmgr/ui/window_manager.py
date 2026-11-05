"""窗口管理器：统一打开、复用、跟踪所有窗口。

【作用】系统支持同时打开多个窗口（详情、阅读、对比……）。窗口的创建、去重、
    关闭后的清理都集中在这里，各窗口之间不需要互相知道对方。
【规则】
    - 详情窗口：同一篇论文默认只开一个（再次打开时把已有窗口提到前台）；
      force_new=True 可强制再开一个。
    - 阅读窗口：同一篇论文默认只开一个；可传 file_id 指定要看的 PDF/翻译；
      restore=True 时还原上次关闭时的页面状态（来自“最近阅读”）。
    - 对比窗口：每次新开一个，可同时开多个。
    - 窗口类用到时才 import（延迟导入），避免循环依赖与启动变慢。
【依赖】ui 下各窗口模块（延迟导入）；services.app_context。
【被谁调用】ui.main_window、detail_window、file_panel 等。
【扩展点】新增一种窗口：在此增加一个 open_xxx 方法即可。
"""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QWidget

from ..services.app_context import AppContext


class WindowManager:
    def __init__(self, ctx: AppContext) -> None:
        self.ctx = ctx
        self._windows: list[QWidget] = []
        self._detail: dict[int, QWidget] = {}
        self._reader: dict[int, QWidget] = {}
        self.main_window: QWidget | None = None

    # ---------- 内部 ----------
    def _track(self, win: QWidget, registry: dict | None = None, key: Any = None) -> QWidget:
        self._windows.append(win)
        if registry is not None:
            registry[key] = win
        win.closed.connect(lambda w=win, r=registry, k=key: self._forget(w, r, k))
        win.show()
        return win

    def _forget(self, win, registry, key) -> None:
        if win in self._windows:
            self._windows.remove(win)
        if registry is not None and registry.get(key) is win:
            del registry[key]

    @staticmethod
    def _raise(win: QWidget) -> QWidget:
        win.showNormal()
        win.raise_()
        win.activateWindow()
        return win

    # ---------- 对外 ----------
    def open_main(self, config=None) -> QWidget:
        """打开一个主窗口（可开多个，共享同一个文献库与事件总线）。"""
        from .main_window import MainWindow
        win = MainWindow(self.ctx, self, config)
        if self.main_window is None:
            self.main_window = win
            win.closed.connect(lambda: setattr(self, "main_window", None))
        return self._track(win)

    def open_detail(self, paper_id: int, force_new: bool = False) -> QWidget:
        from .detail_window import DetailWindow
        if not force_new and paper_id in self._detail:
            return self._raise(self._detail[paper_id])
        win = DetailWindow(self.ctx, self, paper_id)
        return self._track(win, None if force_new else self._detail, paper_id)

    def open_reader(self, paper_id: int, file_id: int | None = None,
                    restore: bool = False) -> QWidget:
        """打开阅读窗口。restore=True 时还原这篇论文上次关闭阅读窗口时的页面状态
        （“最近阅读”菜单使用）；窗口已经开着时只把它提到前台，不改动当前页面。"""
        from .reader_window import ReaderWindow
        if paper_id in self._reader:
            win = self._reader[paper_id]
            if file_id is not None:
                win.show_file(file_id)
            return self._raise(win)
        state = self.ctx.reading.get_state(paper_id) if restore else None
        win = ReaderWindow(self.ctx, self, paper_id, file_id, restore_state=state)
        return self._track(win, self._reader, paper_id)

    def open_compare(self, paper_ids: list[int]) -> QWidget:
        from .compare_window import CompareWindow
        return self._track(CompareWindow(self.ctx, self, paper_ids))

    def open_import_wizard(self, parent: QWidget | None = None) -> None:
        from .import_wizard import ImportWizard
        ImportWizard(parent or self.main_window, self.ctx).exec()

    def close_all(self) -> None:
        for w in list(self._windows):
            w.close()
