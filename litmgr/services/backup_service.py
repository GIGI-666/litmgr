"""备份服务。

【作用】保护数据库：手动/自动备份、列出备份、从备份恢复。
【说明】文献库里的 PDF/翻译等文件本来就是普通文件，整个文献库文件夹复制即可备份；
    这里负责的是 SQLite 数据库（字段值、标签、笔记等）的一致性快照。
    使用 sqlite3 的 backup API，即使数据库正在使用也能得到一致的备份。
【机制】
    - 备份文件：<文献库>/backups/litmgr_YYYYmmdd_HHMMSS.db
    - 自动备份：启动时若最近一次备份超过 min_hours 小时则备份，并只保留最近 keep 份
    - 恢复：把备份内容写回当前数据库（不替换文件，因此无需重启），随后重建全文索引
【依赖】storage.database / library_fs；services.paper_service（重建索引）。
【被谁调用】services.app_context（启动时自动备份）；ui.backup_dialog。
"""

from __future__ import annotations

import re
import sqlite3
import time
from datetime import datetime
from pathlib import Path

from ..core.errors import NotFoundError
from ..core.events import EventBus, Events
from ..storage.database import Database
from ..storage.library_fs import LibraryFS
from .paper_service import PaperService


_AUTO_NAME = re.compile(r"litmgr_\d{8}_\d{6}\.db")   # 自动备份的文件名（无标签后缀）


class BackupService:
    def __init__(self, db: Database, fs: LibraryFS, papers: PaperService,
                 events: EventBus) -> None:
        self.db = db
        self.fs = fs
        self.papers = papers
        self.events = events

    def list_backups(self) -> list[Path]:
        return sorted(self.fs.backups_dir.glob("litmgr_*.db"), reverse=True)

    def backup_now(self, label: str = "") -> Path:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = f"litmgr_{stamp}{('_' + label) if label else ''}.db"
        path = self.fs.backups_dir / name
        self.db.conn.commit()
        dst = sqlite3.connect(path)
        try:
            self.db.conn.backup(dst)
        finally:
            dst.close()
        return path

    def auto_backup(self, keep: int = 10, min_hours: float = 12) -> Path | None:
        """启动时调用：距上次备份足够久才备份；超出 keep 份的旧备份会被清理。"""
        backups = self.list_backups()
        if backups and (time.time() - backups[0].stat().st_mtime) < min_hours * 3600:
            return None
        if self.papers.count() == 0 and not backups:
            return None   # 空库不必备份
        path = self.backup_now()
        # 只清理纯时间戳命名的自动备份；带标签的（手动、恢复前、迁移前快照）一律保留
        autos = [b for b in self.list_backups() if _AUTO_NAME.fullmatch(b.name)]
        for old in autos[keep:]:
            old.unlink(missing_ok=True)
        return path

    def restore(self, backup_path: Path) -> None:
        """从备份恢复。恢复前会先自动为当前状态做一次备份，防止误操作。"""
        backup_path = Path(backup_path)
        if not backup_path.exists():
            raise NotFoundError("备份文件不存在")
        self.backup_now("restore_before")
        src = sqlite3.connect(backup_path)
        try:
            src.backup(self.db.conn)
        finally:
            src.close()
        # 备份可能来自旧版本：补跑迁移，并重设外键/WAL 等连接参数
        self.db.after_replace()
        self.papers.reindex_all()
        self.events.publish(Events.FIELDS_CHANGED)
        self.events.publish(Events.LIBRARY_CHANGED)
