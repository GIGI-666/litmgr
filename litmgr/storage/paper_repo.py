"""论文与字段值仓库（paper / field_value 表）。

【作用】读写论文主记录及其各字段的值。
【职责】
    - 创建/删除论文，更新阅读状态、星级
    - 读写某篇论文的字段值（value_text + value_json）
    - 批量读取多篇论文的值（列表、对比窗口使用，避免 N+1 查询）
【依赖】storage.database；core.models。
【被谁调用】services.paper_service / import_service / compare_service / search_service。
"""

from __future__ import annotations

import json
from typing import Iterable

from ..core.models import FieldValue, Paper
from .database import Database, now_str


class PaperRepo:
    def __init__(self, db: Database) -> None:
        self.db = db

    # ---------- 论文主记录 ----------
    def create(self) -> int:
        t = now_str()
        cur = self.db.execute(
            "INSERT INTO paper(created_at, updated_at) VALUES (?, ?)", (t, t))
        return cur.lastrowid

    def delete(self, paper_id: int) -> None:
        self.db.execute("DELETE FROM paper WHERE id = ?", (paper_id,))

    def exists(self, paper_id: int) -> bool:
        return self.db.query_one("SELECT 1 FROM paper WHERE id=?", (paper_id,)) is not None

    def touch(self, paper_id: int) -> None:
        self.db.execute("UPDATE paper SET updated_at=? WHERE id=?", (now_str(), paper_id))

    def set_status(self, paper_id: int, status: str) -> None:
        self.db.execute("UPDATE paper SET read_status=?, updated_at=? WHERE id=?",
                        (status, now_str(), paper_id))

    def set_rating(self, paper_id: int, rating: int) -> None:
        self.db.execute("UPDATE paper SET rating=?, updated_at=? WHERE id=?",
                        (rating, now_str(), paper_id))

    def set_archived(self, paper_id: int, archived: bool) -> None:
        self.db.execute("UPDATE paper SET archived=?, updated_at=? WHERE id=?",
                        (int(archived), now_str(), paper_id))

    def all_ids(self, include_archived: bool = False) -> list[int]:
        sql = "SELECT id FROM paper"
        if not include_archived:
            sql += " WHERE archived = 0"
        return [r["id"] for r in self.db.query(sql + " ORDER BY id")]

    # ---------- 字段值 ----------
    def set_value(self, paper_id: int, field_id: int, value: FieldValue) -> None:
        self.db.execute(
            "INSERT INTO field_value(paper_id, field_id, value_text, value_json) "
            "VALUES (?,?,?,?) ON CONFLICT(paper_id, field_id) DO UPDATE SET "
            "value_text=excluded.value_text, value_json=excluded.value_json",
            (paper_id, field_id, value.text,
             None if value.json is None else json.dumps(value.json, ensure_ascii=False)),
        )

    def delete_value(self, paper_id: int, field_id: int) -> None:
        self.db.execute("DELETE FROM field_value WHERE paper_id=? AND field_id=?",
                        (paper_id, field_id))

    def get_value(self, paper_id: int, field_id: int) -> FieldValue:
        r = self.db.query_one(
            "SELECT value_text, value_json FROM field_value WHERE paper_id=? AND field_id=?",
            (paper_id, field_id))
        if not r:
            return FieldValue()
        return FieldValue(r["value_text"], json.loads(r["value_json"]) if r["value_json"] else None)

    def values_of_field(self, field_id: int) -> list[tuple[int, FieldValue]]:
        """某字段在所有论文中的值（改字段类型时批量重解析用）。"""
        rows = self.db.query(
            "SELECT paper_id, value_text, value_json FROM field_value WHERE field_id=?",
            (field_id,))
        return [(r["paper_id"], FieldValue(r["value_text"],
                json.loads(r["value_json"]) if r["value_json"] else None)) for r in rows]

    # ---------- 批量读取 ----------
    def load_papers(self, paper_ids: Iterable[int] | None = None) -> list[Paper]:
        """读取论文及其全部字段值。paper_ids 为 None 表示全部（含已归档）。"""
        if paper_ids is None:
            rows = self.db.query("SELECT * FROM paper ORDER BY id")
        else:
            ids = list(paper_ids)
            if not ids:
                return []
            marks = ",".join("?" * len(ids))
            rows = self.db.query(f"SELECT * FROM paper WHERE id IN ({marks})", ids)
        papers = {r["id"]: Paper(id=r["id"], created_at=r["created_at"],
                                 updated_at=r["updated_at"], read_status=r["read_status"],
                                 rating=r["rating"], archived=bool(r["archived"]))
                  for r in rows}
        if not papers:
            return []
        if paper_ids is None:
            vrows = self.db.query("SELECT * FROM field_value")
        else:
            marks = ",".join("?" * len(papers))
            vrows = self.db.query(
                f"SELECT * FROM field_value WHERE paper_id IN ({marks})", list(papers))
        for v in vrows:
            p = papers.get(v["paper_id"])
            if p is not None:
                p.values[v["field_id"]] = FieldValue(
                    v["value_text"], json.loads(v["value_json"]) if v["value_json"] else None)
        # 保持调用方给定的顺序
        if paper_ids is not None:
            return [papers[i] for i in ids if i in papers]
        return list(papers.values())
