"""阅读历史仓库（reading_history 表）。

【作用】保存“最近阅读了哪些论文”以及关闭阅读窗口时的页面状态（不透明的 JSON 文本）。
【职责】
    - touch：打开论文时记录/刷新阅读时间，保留已有的页面状态
    - save_state：关闭窗口时写入页面状态（只更新已有记录，不会因论文已删除而复活）
    - list_recent：按最近阅读时间倒序返回
    - trim：只保留最近 N 条
【依赖】storage.database。
【被谁调用】services.reading_history_service。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from .database import Database

_STAMP_FMT = "%Y-%m-%d %H:%M:%S.%f"

@dataclass
class ReadingRecord:
    paper_id: int
    last_opened: str
    state_json: str


class ReadingRepo:
    def __init__(self, db: Database) -> None:
        self.db = db

    def touch(self, paper_id: int) -> None:
        """记录一次打开：不存在则新增，存在则只刷新时间（保留旧状态）。"""
        # 同一秒内连续打开多篇时需要区分先后，所以使用严格递增的时间戳
        t = self._next_stamp()
        self.db.execute(
            "INSERT INTO reading_history(paper_id,last_opened,state_json) VALUES (?,?,'{}') "
            "ON CONFLICT(paper_id) DO UPDATE SET last_opened=excluded.last_opened",
            (paper_id, t))

    def _next_stamp(self) -> str:
        """生成严格递增的时间戳（微秒精度）：不早于库中最大值，保证排序确定。"""
        row = self.db.query_one("SELECT MAX(last_opened) AS m FROM reading_history")
        now = datetime.now()
        if row and row["m"]:
            try:
                last = datetime.strptime(row["m"].split("#")[0], _STAMP_FMT)
            except ValueError:
                # 兼容旧格式（无微秒的 "YYYY-MM-DD HH:MM:SS"）
                last = datetime.strptime(row["m"].split("#")[0][:19], "%Y-%m-%d %H:%M:%S")
            if now <= last:  # 与最后一条同刻或时钟回拨
                now = last + timedelta(microseconds=1)
        return now.strftime(_STAMP_FMT)

    def save_state(self, paper_id: int, state_json: str) -> None:
        self.db.execute("UPDATE reading_history SET state_json=? WHERE paper_id=?",
                        (state_json, paper_id))

    def get(self, paper_id: int) -> ReadingRecord | None:
        r = self.db.query_one("SELECT * FROM reading_history WHERE paper_id=?", (paper_id,))
        return ReadingRecord(r["paper_id"], r["last_opened"], r["state_json"]) if r else None

    def list_recent(self, limit: int) -> list[ReadingRecord]:
        return [ReadingRecord(r["paper_id"], r["last_opened"], r["state_json"])
                for r in self.db.query(
                    "SELECT * FROM reading_history ORDER BY last_opened DESC LIMIT ?", (limit,))]

    def trim(self, keep: int) -> None:
        """只保留最近 keep 条，其余删除。"""
        self.db.execute(
            "DELETE FROM reading_history WHERE paper_id NOT IN ("
            "SELECT paper_id FROM reading_history ORDER BY last_opened DESC LIMIT ?)", (keep,))

    def remove(self, paper_id: int) -> None:
        self.db.execute("DELETE FROM reading_history WHERE paper_id=?", (paper_id,))

    def clear(self) -> None:
        self.db.execute("DELETE FROM reading_history")
