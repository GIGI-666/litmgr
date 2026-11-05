"""笔记仓库（note 表）。

【作用】保存论文的阅读笔记/摘录。一篇论文可有多条笔记。
【依赖】storage.database；core.models。
【被谁调用】services.note_service。
"""

from __future__ import annotations

from ..core.models import Note
from .database import Database, now_str


class NoteRepo:
    def __init__(self, db: Database) -> None:
        self.db = db

    def list_for_paper(self, paper_id: int) -> list[Note]:
        return [Note(r["id"], r["paper_id"], r["content"], r["created_at"], r["updated_at"])
                for r in self.db.query(
                    "SELECT * FROM note WHERE paper_id=? ORDER BY created_at DESC, id DESC",
                    (paper_id,))]

    def add(self, paper_id: int, content: str) -> int:
        t = now_str()
        cur = self.db.execute(
            "INSERT INTO note(paper_id,content,created_at,updated_at) VALUES (?,?,?,?)",
            (paper_id, content, t, t))
        return cur.lastrowid

    def update(self, note_id: int, content: str) -> None:
        self.db.execute("UPDATE note SET content=?, updated_at=? WHERE id=?",
                        (content, now_str(), note_id))

    def delete(self, note_id: int) -> None:
        self.db.execute("DELETE FROM note WHERE id=?", (note_id,))

    def all_text(self, paper_id: int) -> str:
        """某论文全部笔记拼接（用于建全文索引）。"""
        return "\n".join(n.content for n in self.list_for_paper(paper_id))
