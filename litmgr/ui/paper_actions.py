"""论文操作集合（右键菜单、批量操作、导出）。

【作用】把“对选中的若干论文做什么”集中在一处：打开/阅读/对比、设置状态与星级、
    加入分组/打标签、导出、删除。主窗口只负责决定“选中了哪些”，具体操作都在这里。
【用法】actions = PaperActions(main_window, ctx, windows)；
    actions.build_row_menu(menu, ids) 把菜单项加到右键菜单；其余方法可直接绑定到工具栏。
【依赖】services（经 AppContext）；ui.organize_panel（分组/标签选择对话框）。
【被谁调用】ui.main_window。
【扩展点】新增批量操作：写一个方法并在 build_row_menu 里加一行菜单项。
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QMenu, QMessageBox, QWidget

from ..core.models import READ_STATUS
from ..services.app_context import AppContext
from .organize_panel import edit_collections_for, edit_tags_for
from .utils import guarded

MAX_READERS_AT_ONCE = 4   # 一次最多同时打开几个阅读窗口，避免误操作


class PaperActions:
    def __init__(self, widget: QWidget, ctx: AppContext, windows) -> None:
        self.widget = widget      # 对话框的父窗口
        self.ctx = ctx
        self.windows = windows

    # ---------- 打开 ----------
    def read(self, ids: list[int]) -> None:
        for pid in ids[:MAX_READERS_AT_ONCE]:
            self.windows.open_reader(pid)

    def compare(self, ids: list[int]) -> None:
        if ids:
            self.windows.open_compare(ids)

    @guarded
    def new_blank(self) -> None:
        pid = self.ctx.papers.create()
        self.windows.open_detail(pid)

    # ---------- 右键菜单 ----------
    def build_row_menu(self, menu: QMenu, ids: list[int]) -> None:
        if len(ids) == 1:
            menu.addAction("打开详情", lambda: self.windows.open_detail(ids[0]))
            menu.addAction("在新窗口打开详情",
                           lambda: self.windows.open_detail(ids[0], force_new=True))
        menu.addAction("阅读（PDF + 翻译）", lambda: self.read(ids))
        menu.addAction("对比选中的论文", lambda: self.compare(ids))
        menu.addSeparator()
        sm = menu.addMenu("设置阅读状态")
        for k, v in READ_STATUS.items():
            sm.addAction(v, lambda k=k: self.set_status(ids, k))
        rm = menu.addMenu("设置星级")
        for n in range(0, 6):
            rm.addAction("未评分" if n == 0 else "★" * n, lambda n=n: self.set_rating(ids, n))
        menu.addAction("加入分组…", lambda: edit_collections_for(self.widget, self.ctx, ids))
        menu.addAction("打标签…", lambda: edit_tags_for(self.widget, self.ctx, ids))
        menu.addSeparator()
        menu.addAction("导出选中为卡片 txt…", lambda: self.export_selected("txt", ids))
        menu.addAction("导出选中为 CSV…", lambda: self.export_selected("csv", ids))
        menu.addSeparator()
        menu.addAction("删除论文…", lambda: self.delete(ids))

    # ---------- 批量修改 ----------
    @guarded
    def set_status(self, ids: list[int], status: str) -> None:
        for i in ids:
            self.ctx.papers.set_status(i, status)

    @guarded
    def set_rating(self, ids: list[int], n: int) -> None:
        for i in ids:
            self.ctx.papers.set_rating(i, n)

    @guarded
    def delete(self, ids: list[int]) -> None:
        if QMessageBox.question(
                self.widget, "删除论文",
                f"永久删除选中的 {len(ids)} 篇论文及其库内文件副本？\n"
                "此操作不可撤销（你的源文件不受影响）。") == QMessageBox.Yes:
            for i in ids:
                self.ctx.papers.delete(i)

    # ---------- 导出 ----------
    @guarded
    def export_selected(self, fmt: str, ids: list[int]) -> None:
        if fmt == "txt":
            d = QFileDialog.getExistingDirectory(self.widget, "选择导出到的文件夹")
            if d:
                out = self.ctx.export.export("txt", ids, Path(d))
                QMessageBox.information(self.widget, "导出完成", f"已导出 {len(out)} 个卡片文件。")
        else:
            path, _ = QFileDialog.getSaveFileName(self.widget, "导出 CSV", "论文列表.csv",
                                                  "CSV (*.csv)")
            if path:
                self.ctx.export.export("csv", ids, Path(path))

    @guarded
    def export_all_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self.widget, "导出全部论文", "全部论文.csv",
                                              "CSV (*.csv)")
        if path:
            self.ctx.export.export("csv", [p.id for p in self.ctx.papers.list_titles()], Path(path))
