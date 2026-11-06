"""备份与恢复对话框。

【作用】查看数据库备份、立即备份、从某个备份恢复、打开备份文件夹。
【说明】备份的是数据库（字段内容、标签、笔记等）；PDF/翻译等文件在文献库文件夹里，
    复制整个文献库文件夹即可完整备份。恢复前系统会先自动为当前状态备份一次。
【依赖】services.backup_service（通过 AppContext）。
【被谁调用】ui.main_window（文件 -> 备份与恢复）。
"""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QLabel, QListWidget, QListWidgetItem, QMessageBox,
                               QVBoxLayout)

from ..services.app_context import AppContext
from .utils import add_buttons, guarded, open_path


class BackupDialog(QDialog):
    def __init__(self, parent, ctx: AppContext) -> None:
        super().__init__(parent)
        self.ctx = ctx
        self.setWindowTitle("备份与恢复")
        self.resize(520, 420)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("数据库备份列表（启动时会自动备份，最近的在最上面）："))
        self.list = QListWidget()
        lay.addWidget(self.list, 1)
        add_buttons(lay, [("立即备份", self.backup), ("从选中的备份恢复", self.restore),
                          ("检查多余文件", self.clean_orphans),
                          ("打开备份文件夹", lambda: open_path(ctx.fs.backups_dir))], stretch=False)
        self.refresh()

    def refresh(self) -> None:
        self.list.clear()
        for p in self.ctx.backup.list_backups():
            st = p.stat()
            it = QListWidgetItem(f"{datetime.fromtimestamp(st.st_mtime):%Y-%m-%d %H:%M:%S}   "
                                 f"{st.st_size / 1024:.0f} KB   {p.name}")
            it.setData(Qt.UserRole, str(p))
            self.list.addItem(it)

    @guarded
    def backup(self) -> None:
        self.ctx.backup.backup_now("manual")
        self.refresh()

    @guarded
    def restore(self) -> None:
        it = self.list.currentItem()
        if not it:
            return
        if QMessageBox.question(
                self, "恢复备份",
                "用选中的备份覆盖当前数据库内容？\n（恢复前会自动备份当前状态）") == QMessageBox.Yes:
            self.ctx.backup.restore(it.data(Qt.UserRole))
            self.refresh()
            QMessageBox.information(self, "完成", "已恢复。")
            self.clean_orphans(quiet=True)

    @guarded
    def clean_orphans(self, quiet: bool = False) -> None:
        """找出文献库里数据库没登记的文件（恢复旧备份后常会出现），确认后删除。"""
        orphans = self.ctx.files.find_orphans()
        if not orphans:
            if not quiet:      # 用户主动点按钮时才提示“没有”
                QMessageBox.information(self, "检查多余文件", "没有发现多余文件。")
            return
        size = sum(p.stat().st_size for p in orphans if p.exists()) / 1024 / 1024
        if QMessageBox.question(
                self, "发现多余文件",
                f"文献库里有 {len(orphans)} 个文件（约 {size:.1f} MB）没有登记在数据库中，\n"
                "多半是恢复旧备份后遗留的。删除它们？（删除后不可恢复）") == QMessageBox.Yes:
            n = self.ctx.files.delete_orphans(orphans)
            QMessageBox.information(self, "完成", f"已删除 {n} 个多余文件。")
