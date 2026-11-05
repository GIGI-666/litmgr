"""修改历史与待归类内容仓库（change_log / pending_content 表）。

【作用】
    - change_log：记录每次字段值修改的“旧值 -> 新值”，用于查看历史与撤销。
    - pending_content：导入时无法归入任何字段的内容，暂存等待用户归类。
【依赖】storage.database；core.models。
【被谁调用】services.history_service、services.paper_service、services.import_service。
"""

from __future__ import annotations

from ..core.models import ChangeLogEntry, PendingContent
from .database import Database, now_str


def _entry(r) -> ChangeLogEntry:
    return ChangeLogEntry(r["id"], r["paper_id"], r["field_id"], r["field_name"],
                          r["old_value"], r["new_value"], r["changed_at"], bool(r["undone"]))


class LogRepo:
    def __init__(self, db: Database) -> None:
        self.db = db

    # ---------- 修改历史 ----------
    def add_change(self, paper_id: int, field_id: int | None, field_name: str,
                   old: str, new: str) -> int:
        cur = self.db.execute(
            "INSERT INTO change_log(paper_id,field_id,field_name,old_value,new_value,changed_at)"
            " VALUES (?,?,?,?,?,?)", (paper_id, field_id, field_name, old, new, now_str()))
        return cur.lastrowid

    def get_change(self, entry_id: int) -> ChangeLogEntry | None:
        r = self.db.query_one("SELECT * FROM change_log WHERE id=?", (entry_id,))
        return _entry(r) if r else None

    def history_of_paper(self, paper_id: int, limit: int = 200) -> list[ChangeLogEntry]:
        return [_entry(r) for r in self.db.query(
            "SELECT * FROM change_log WHERE paper_id=? ORDER BY id DESC LIMIT ?",
            (paper_id, limit))]

    def recent(self, limit: int = 100) -> list[ChangeLogEntry]:
        return [_entry(r) for r in self.db.query(
            "SELECT * FROM change_log ORDER BY id DESC LIMIT ?", (limit,))]

    def last_undoable(self) -> ChangeLogEntry | None:
        r = self.db.query_one(
            "SELECT * FROM change_log WHERE undone=0 AND field_id IS NOT NULL "
            "ORDER BY id DESC LIMIT 1")
        return _entry(r) if r else None

    def mark_undone(self, entry_id: int) -> None:
        self.db.execute("UPDATE change_log SET undone=1 WHERE id=?", (entry_id,))

    # ---------- 待归类内容 ----------
    def add_pending(self, paper_id: int, label: str, content: str) -> int:
        cur = self.db.execute(
            "INSERT INTO pending_content(paper_id,label,content) VALUES (?,?,?)",
            (paper_id, label, content))
        return cur.lastrowid

    def list_pending(self, paper_id: int | None = None) -> list[PendingContent]:
        if paper_id is None:
            rows = self.db.query("SELECT * FROM pending_content ORDER BY paper_id, id")
        else:
            rows = self.db.query("SELECT * FROM pending_content WHERE paper_id=? ORDER BY id",
                                 (paper_id,))
        return [PendingContent(r["id"], r["paper_id"], r["label"], r["content"]) for r in rows]

    def get_pending(self, pid: int) -> PendingContent | None:
        r = self.db.query_one("SELECT * FROM pending_content WHERE id=?", (pid,))
        return PendingContent(r["id"], r["paper_id"], r["label"], r["content"]) if r else None

    def delete_pending(self, pid: int) -> None:
        self.db.execute("DELETE FROM pending_content WHERE id=?", (pid,))
