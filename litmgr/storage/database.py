"""SQLite 连接与迁移管理。

【作用】封装数据库连接，并在打开时自动执行迁移脚本（migrations/*.sql），
    让数据库结构可以随版本平滑升级而不丢用户数据。
【职责】
    - 打开数据库（WAL、外键）
    - 提供 query / execute / transaction 等简洁接口，供各仓库使用
    - 按 PRAGMA user_version 顺序执行尚未执行的迁移
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

    def __init__(self, path: Path | str) -> None:
        self.path = str(path)
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        if self.path != ":memory:":
            self.conn.execute("PRAGMA journal_mode = WAL")
        self._depth = 0
        self.migrate()

    # ---------- 迁移 ----------
    def migrate(self) -> None:
        """执行所有版本号大于当前 user_version 的迁移脚本。"""
        current = self.conn.execute("PRAGMA user_version").fetchone()[0]
        scripts = sorted(
            (int(m.group(1)), p)
            for p in MIGRATIONS_DIR.glob("*.sql")
            if (m := _MIGRATION_RE.match(p.name))
        )
        for version, script in scripts:
            if version <= current:
                continue
            self.conn.executescript(script.read_text(encoding="utf-8"))
            self.conn.execute(f"PRAGMA user_version = {version}")
            self.conn.commit()

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
