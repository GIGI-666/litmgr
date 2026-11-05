"""论文文件仓库（paper_file 表）。

【作用】记录每篇论文关联的文件：卡片、PDF、翻译 md、附件，以及它们在文献库内的相对路径。
【职责】只管数据库记录；真正的文件复制/删除在 storage.library_fs。
【依赖】storage.database；core.models。
【被谁调用】services.paper_service / import_service。
"""

from __future__ import annotations

from ..core.models import PaperFile
from .database import Database, now_str


def _row(r) -> PaperFile:
    return PaperFile(id=r["id"], paper_id=r["paper_id"], kind=r["kind"], subtype=r["subtype"],
                     rel_path=r["rel_path"], display_name=r["display_name"],
                     sha256=r["sha256"], added_at=r["added_at"])


class FileRepo:
    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, paper_id: int, kind: str, rel_path: str, display_name: str,
            subtype: str = "", sha256: str = "") -> int:
        cur = self.db.execute(
            "INSERT INTO paper_file(paper_id,kind,subtype,rel_path,display_name,sha256,added_at)"
            " VALUES (?,?,?,?,?,?,?)",
            (paper_id, kind, subtype, rel_path, display_name, sha256, now_str()))
        return cur.lastrowid

    def get(self, file_id: int) -> PaperFile | None:
        r = self.db.query_one("SELECT * FROM paper_file WHERE id=?", (file_id,))
        return _row(r) if r else None

    def list_for_paper(self, paper_id: int, kind: str | None = None) -> list[PaperFile]:
        sql, params = "SELECT * FROM paper_file WHERE paper_id=?", [paper_id]
        if kind:
            sql += " AND kind=?"
            params.append(kind)
        return [_row(r) for r in self.db.query(sql + " ORDER BY id", params)]

    def find_by_hash(self, sha256: str, kind: str | None = None) -> list[PaperFile]:
        sql, params = "SELECT * FROM paper_file WHERE sha256=? AND sha256<>''", [sha256]
        if kind:
            sql += " AND kind=?"
            params.append(kind)
        return [_row(r) for r in self.db.query(sql, params)]

    def update_subtype(self, file_id: int, subtype: str) -> None:
        self.db.execute("UPDATE paper_file SET subtype=? WHERE id=?", (subtype, file_id))

    def update_display_name(self, file_id: int, name: str) -> None:
        self.db.execute("UPDATE paper_file SET display_name=? WHERE id=?", (name, file_id))

    def update_content(self, file_id: int, sha256: str) -> None:
        self.db.execute("UPDATE paper_file SET sha256=? WHERE id=?", (sha256, file_id))

    def delete(self, file_id: int) -> None:
        self.db.execute("DELETE FROM paper_file WHERE id=?", (file_id,))
