"""SQLite 连接与迁移管理。

【作用】封装数据库连接，并在打开时自动执行迁移脚本（migrations/*.sql），
    让数据库结构可以随版本平滑升级而不丢用户数据。
【职责】
    - 打开数据库（WAL、外键）
    - 提供 query / execute / transaction 等简洁接口，供各仓库使用
      （单条 execute 在最外层会立即提交；批量操作请包在 transaction() 里，快得多）
    - 按 PRAGMA user_version 顺序执行尚未执行的迁移（原子执行，升级前自动备份）
【依赖】标准库 sqlite3；core.errors。
【被谁调用】所有 storage.*_repo；services.app_context 创建它。
【扩展点】要改表结构：新增 migrations/NNNN_说明.sql（NNNN 递增），不要修改旧迁移。
"""

from __future__ import annotations

import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Iterator

MIGRATIONS_DIR = Path(__file__).parent / "migrations"
_MIGRATION_RE = re.compile(r"^(\d{4})_.*\.sql$")


def now_str() -> str:
    """统一的时间戳格式（本地时间，到秒）。"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class Database:
    """对 sqlite3 连接的薄封装。GUI 单线程使用。"""

    def __init__(self, path: Path | str, backup_dir: Path | str | None = None) -> None:
        """backup_dir：升级数据库结构前，把旧库快照存到这里（None 则不备份）。"""
        self.path = str(path)
        self.backup_dir = Path(backup_dir) if backup_dir else None
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._depth = 0
        self._configure()
        self.migrate()

    def _configure(self) -> None:
        """连接级设置。整库被替换（如恢复备份）后也要重新执行。"""
        self.conn.execute("PRAGMA foreign_keys = ON")
        if self.path != ":memory:":
            self.conn.execute("PRAGMA journal_mode = WAL")
            # WAL 模式下 NORMAL 仍能保证数据库不损坏，只是极端断电时可能丢最后几次提交，
            # 换来写入速度大幅提升
            self.conn.execute("PRAGMA synchronous = NORMAL")

    def after_replace(self) -> None:
        """整库内容被替换后调用（恢复备份）：重设连接参数，并把旧结构的库升级到当前版本。"""
        self._configure()
        self.migrate()

    # ---------- 迁移 ----------
    def migrate(self) -> None:
        """执行所有版本号大于当前 user_version 的迁移脚本。

        每个迁移脚本与“版本号更新”放在同一个事务里：要么整个迁移成功，要么完全不生效。
        升级一个已有数据的库之前，会先自动做一份快照备份。
        """
        current = self.conn.execute("PRAGMA user_version").fetchone()[0]
        scripts = sorted(
            (int(m.group(1)), p)
            for p in MIGRATIONS_DIR.glob("*.sql")
            if (m := _MIGRATION_RE.match(p.name))
        )
        pending = [(v, p) for v, p in scripts if v > current]
        if not pending:
            return
        if current > 0:
            self._snapshot_before_migrate(current)
        for version, script in pending:
            sql = (f"BEGIN;\n{script.read_text(encoding='utf-8')}\n"
                   f"PRAGMA user_version = {version};\nCOMMIT;")
            try:
                self.conn.executescript(sql)
            except Exception:
                if self.conn.in_transaction:
                    self.conn.rollback()
                raise

    def _snapshot_before_migrate(self, from_version: int) -> None:
        """升级前备份：升级出问题时可以从这份快照恢复。"""
        if self.backup_dir is None or self.path == ":memory:":
            return
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = self.backup_dir / f"litmgr_{stamp}_premigrate_v{from_version}.db"
        self.conn.commit()
        dst = sqlite3.connect(target)
        try:
            self.conn.backup(dst)
        finally:
            dst.close()

    # ---------- 查询接口 ----------
    def query(self, sql: str, params: Iterable[Any] = ()) -> list[sqlite3.Row]:
        return self.conn.execute(sql, tuple(params)).fetchall()

    def query_one(self, sql: str, params: Iterable[Any] = ()) -> sqlite3.Row | None:
        return self.conn.execute(sql, tuple(params)).fetchone()

    def execute(self, sql: str, params: Iterable[Any] = ()) -> sqlite3.Cursor:
        cur = self.conn.execute(sql, tuple(params))
        if self._depth == 0:
            self.conn.commit()
        return cur

    def executemany(self, sql: str, rows: Iterable[Iterable[Any]]) -> None:
        self.conn.executemany(sql, rows)
        if self._depth == 0:
            self.conn.commit()

    @contextmanager
    def transaction(self) -> Iterator[None]:
        """事务上下文，可嵌套；最外层成功提交、异常回滚。"""
        self._depth += 1
        try:
            yield
        except BaseException:
            self._depth -= 1
            if self._depth == 0:
                self.conn.rollback()
            raise
        else:
            self._depth -= 1
            if self._depth == 0:
                self.conn.commit()

    def close(self) -> None:
        self.conn.commit()
        self.conn.close()
