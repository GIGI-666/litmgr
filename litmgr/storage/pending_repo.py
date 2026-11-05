"""待归类内容仓库（pending_content 表）。

【作用】导入时无法归入任何字段的内容，暂存在这里，等用户在论文详情里决定并入哪个字段。
【依赖】storage.database；core.models。
【被谁调用】services.pending_service、services.import_service（通过 PendingService）。
"""

from __future__ import annotations

from ..core.models import PendingContent
from .database import Database


def _pending(r) -> PendingContent:
    return PendingContent(r["id"], r["paper_id"], r["label"], r["content"])


class PendingRepo:
    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, paper_id: int, label: str, content: str) -> int:
        cur = self.db.execute(
            "INSERT INTO pending_content(paper_id,label,content) VALUES (?,?,?)",
            (paper_id, label, content))
        return cur.lastrowid

    def list(self, paper_id: int | None = None) -> list[PendingContent]:
        if paper_id is None:
            rows = self.db.query("SELECT * FROM pending_content ORDER BY paper_id, id")
        else:
            rows = self.db.query("SELECT * FROM pending_content WHERE paper_id=? ORDER BY id",
                                 (paper_id,))
        return [_pending(r) for r in rows]

    def get(self, pid: int) -> PendingContent | None:
        r = self.db.query_one("SELECT * FROM pending_content WHERE id=?", (pid,))
        return _pending(r) if r else None

    def delete(self, pid: int) -> None:
        self.db.execute("DELETE FROM pending_content WHERE id=?", (pid,))
