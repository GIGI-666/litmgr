"""备份服务。

【作用】保护数据库：手动/自动备份、列出备份、从备份恢复。
【说明】文献库里的 PDF/翻译等文件本来就是普通文件，整个文献库文件夹复制即可备份；
    这里负责的是 SQLite 数据库（字段值、标签、笔记等）的一致性快照。
    使用 sqlite3 的 backup API，即使数据库正在使用也能得到一致的备份。
【机制】
    - 备份文件：<文献库>/backups/litmgr_YYYYmmdd_HHMMSS.微秒.db
    - 自动备份：启动时若最近一次备份超过 min_hours 小时则备份，并只保留最近 keep 份
    - 恢复：把备份内容写回当前数据库（不替换文件，因此无需重启），随后重建全文索引
【依赖】storage.database / library_fs；services.paper_service（重建索引）。
【被谁调用】services.app_context（启动时自动备份）；ui.backup_dialog。
"""

from __future__ import annotations

import re
import sqlite3
import tempfile
import time
from contextlib import closing
from datetime import datetime
from pathlib import Path

from ..core.errors import NotFoundError, ValidationError
from ..core.events import EventBus, Events
from ..storage.database import Database
from ..storage.library_fs import LibraryFS
from .paper_service import PaperService


_AUTO_NAME = re.compile(r"litmgr_\d{8}_\d{6}(?:\.\d{6})?\.db")


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
        if self.db.conn.in_transaction:
            raise ValidationError("请等待当前数据库操作结束，再创建备份。")
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S.%f")
        name = f"litmgr_{stamp}{('_' + label) if label else ''}.db"
        path = self.fs.backups_dir / name
        with tempfile.TemporaryDirectory(prefix=".backup-", dir=self.fs.backups_dir) as temp:
            staged = Path(temp) / "backup.db"
            with closing(sqlite3.connect(staged)) as dst:
                self.db.conn.backup(dst)
            # 同一文件系统内改名，失败时列表不会出现半成品。在 Windows 上目标存在时拒绝改名。
            if path.exists():
                raise ValidationError("备份文件已存在，请重试。")
            staged.rename(path)
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
        if self.db.conn.in_transaction:
            raise ValidationError("请等待当前数据库操作结束，再恢复备份。")
        backup_path = Path(backup_path)
        if not backup_path.exists():
            raise NotFoundError("备份文件不存在")
        if backup_path.resolve() == self.fs.db_path.resolve():
            raise ValidationError("请选择备份文件。")
        with tempfile.TemporaryDirectory(prefix=".restore-", dir=self.fs.backups_dir) as temp:
            staged = Path(temp) / "candidate.db"
            migration_backups = staged.parent / "migrations"
            try:
                with closing(sqlite3.connect(backup_path.resolve().as_uri() + "?mode=ro", uri=True)) as src:
                    with closing(sqlite3.connect(staged)) as dst:
                        src.backup(dst)
                        version = dst.execute("PRAGMA user_version").fetchone()[0]
                        if not 0 < version <= self.db.query_one("PRAGMA user_version")[0]:
                            raise ValidationError("备份的数据库版本不受支持。")
                        if dst.execute("PRAGMA quick_check").fetchall() != [("ok",)]:
                            raise ValidationError("备份未通过完整性检查。")
                candidate = Database(staged, backup_dir=migration_backups)
            except sqlite3.Error as exc:
                raise ValidationError(f"无法读取或升级备份：{exc}") from exc
            try:
                self._validate_candidate(candidate)
                self.backup_now("restore_before")
                for checkpoint in migration_backups.glob("*.db"):
                    target = self.fs.backups_dir / checkpoint.name
                    if target.exists():
                        raise ValidationError("迁移前备份文件已存在，请重试。")
                    checkpoint.rename(target)
                candidate.conn.backup(self.db.conn)
            finally:
                candidate.close()
        self.db.after_replace()
        self.papers.reindex_all()
        self.events.publish(Events.FIELDS_CHANGED)
        self.events.publish(Events.LIBRARY_CHANGED)

    def _validate_candidate(self, candidate: Database) -> None:
        """先在独立副本检查文献库表结构和外键，再允许替换当前库。"""
        if candidate.query("PRAGMA foreign_key_check"):
            raise ValidationError("备份中存在失效的数据库关联。")
        for table in self.db.query("PRAGMA table_list"):
            if table["type"] not in ("table", "virtual") or table["name"].startswith("sqlite_"):
                continue
            name = table["name"]
            sql = "SELECT name FROM pragma_table_info(?)"
            required = {col["name"] for col in self.db.query(sql, (name,))}
            actual = {col["name"] for col in candidate.query(sql, (name,))}
            if not required <= actual:
                raise ValidationError(f"备份缺少文献库表或字段：{name}")
