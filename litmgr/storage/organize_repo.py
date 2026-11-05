"""整理类数据仓库：标签、分组、保存的检索。

【作用】读写 tag/paper_tag、collection/paper_collection、saved_view 三组表。
【说明】这里的“标签”是系统级标签（用于整理论文），与字段类型“多标签”不同：
    后者是论文卡片里的某个字段内容。
【依赖】storage.database；core.models。
【被谁调用】services.organize_service、services.search_service。
"""

from __future__ import annotations

import json

from ..core.models import Collection, SavedView, Tag
from .database import Database, now_str


class OrganizeRepo:
    def __init__(self, db: Database) -> None:
        self.db = db

    # ---------- 标签 ----------
    def list_tags(self) -> list[Tag]:
        return [Tag(r["id"], r["name"], r["color"])
                for r in self.db.query("SELECT * FROM tag ORDER BY name")]

    def add_tag(self, name: str, color: str = "") -> int:
        cur = self.db.execute("INSERT INTO tag(name,color) VALUES (?,?)", (name, color))
        return cur.lastrowid

    def find_tag(self, name: str) -> Tag | None:
        r = self.db.query_one("SELECT * FROM tag WHERE name=?", (name,))
        return Tag(r["id"], r["name"], r["color"]) if r else None

    def rename_tag(self, tag_id: int, name: str) -> None:
        self.db.execute("UPDATE tag SET name=? WHERE id=?", (name, tag_id))

    def delete_tag(self, tag_id: int) -> None:
        self.db.execute("DELETE FROM tag WHERE id=?", (tag_id,))

    def tags_of_paper(self, paper_id: int) -> list[Tag]:
        rows = self.db.query(
            "SELECT t.* FROM tag t JOIN paper_tag pt ON pt.tag_id=t.id "
            "WHERE pt.paper_id=? ORDER BY t.name", (paper_id,))
        return [Tag(r["id"], r["name"], r["color"]) for r in rows]

    def tag_map(self) -> dict[int, list[str]]:
        """所有论文的标签名（列表“标签”列用）。"""
        out: dict[int, list[str]] = {}
        for r in self.db.query(
                "SELECT pt.paper_id, t.name FROM paper_tag pt JOIN tag t ON t.id=pt.tag_id "
                "ORDER BY t.name"):
            out.setdefault(r["paper_id"], []).append(r["name"])
        return out

    def paper_ids_with_tag(self, tag_id: int) -> set[int]:
        return {r["paper_id"] for r in self.db.query(
            "SELECT paper_id FROM paper_tag WHERE tag_id=?", (tag_id,))}

    def paper_ids_in_collection(self, cid: int) -> set[int]:
        return {r["paper_id"] for r in self.db.query(
            "SELECT paper_id FROM paper_collection WHERE collection_id=?", (cid,))}

    def collection_counts(self) -> dict[int, int]:
        return {r["collection_id"]: r["n"] for r in self.db.query(
            "SELECT collection_id, COUNT(*) AS n FROM paper_collection GROUP BY collection_id")}

    def tag_counts(self) -> dict[int, int]:
        return {r["tag_id"]: r["n"] for r in self.db.query(
            "SELECT tag_id, COUNT(*) AS n FROM paper_tag GROUP BY tag_id")}

    def attach_tag(self, paper_id: int, tag_id: int) -> None:
        self.db.execute("INSERT OR IGNORE INTO paper_tag(paper_id,tag_id) VALUES (?,?)",
                        (paper_id, tag_id))

    def detach_tag(self, paper_id: int, tag_id: int) -> None:
        self.db.execute("DELETE FROM paper_tag WHERE paper_id=? AND tag_id=?",
                        (paper_id, tag_id))

    # ---------- 分组 ----------
    def list_collections(self) -> list[Collection]:
        return [Collection(r["id"], r["name"], r["sort_order"])
                for r in self.db.query("SELECT * FROM collection ORDER BY sort_order, name")]

    def add_collection(self, name: str) -> int:
        cur = self.db.execute("INSERT INTO collection(name) VALUES (?)", (name,))
        return cur.lastrowid

    def rename_collection(self, cid: int, name: str) -> None:
        self.db.execute("UPDATE collection SET name=? WHERE id=?", (name, cid))

    def delete_collection(self, cid: int) -> None:
        self.db.execute("DELETE FROM collection WHERE id=?", (cid,))

    def collections_of_paper(self, paper_id: int) -> list[Collection]:
        rows = self.db.query(
            "SELECT c.* FROM collection c JOIN paper_collection pc ON pc.collection_id=c.id "
            "WHERE pc.paper_id=? ORDER BY c.name", (paper_id,))
        return [Collection(r["id"], r["name"], r["sort_order"]) for r in rows]

    def add_to_collection(self, paper_id: int, cid: int) -> None:
        self.db.execute("INSERT OR IGNORE INTO paper_collection VALUES (?,?)", (paper_id, cid))

    def remove_from_collection(self, paper_id: int, cid: int) -> None:
        self.db.execute("DELETE FROM paper_collection WHERE paper_id=? AND collection_id=?",
                        (paper_id, cid))

    # ---------- 保存的检索 ----------
    def list_views(self) -> list[SavedView]:
        return [SavedView(r["id"], r["name"], json.loads(r["query_json"]))
                for r in self.db.query("SELECT * FROM saved_view ORDER BY name")]

    def save_view(self, name: str, query: dict) -> int:
        q = json.dumps(query, ensure_ascii=False)
        r = self.db.query_one("SELECT id FROM saved_view WHERE name=?", (name,))
        if r:
            self.db.execute("UPDATE saved_view SET query_json=? WHERE id=?", (q, r["id"]))
            return r["id"]
        cur = self.db.execute(
            "INSERT INTO saved_view(name,query_json,created_at) VALUES (?,?,?)",
            (name, q, now_str()))
        return cur.lastrowid

    def delete_view(self, vid: int) -> None:
        self.db.execute("DELETE FROM saved_view WHERE id=?", (vid,))
