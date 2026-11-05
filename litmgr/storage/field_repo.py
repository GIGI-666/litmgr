"""字段定义仓库（field_def 表）。

【作用】读写“字段定义”：字段名、类型、候选项、别名、角色、分组、排序、是否归档。
【职责】只做数据读写；字段名查重、类型转换等业务规则在 services.field_service。
【依赖】storage.database；core.models。
【被谁调用】services.field_service、services.paper_service、importers（通过服务）。
"""

from __future__ import annotations

import json

from ..core.models import FieldDef
from .database import Database


def _row_to_field(r) -> FieldDef:
    return FieldDef(
        id=r["id"], name=r["name"], type=r["type"],
        options=json.loads(r["options_json"] or "[]"),
        aliases=json.loads(r["aliases_json"] or "[]"),
        role=r["role"], group_name=r["group_name"], sort_order=r["sort_order"],
        show_in_list=bool(r["show_in_list"]), archived=bool(r["archived"]),
    )


class FieldRepo:
    def __init__(self, db: Database) -> None:
        self.db = db

    def list(self, include_archived: bool = False) -> list[FieldDef]:
        sql = "SELECT * FROM field_def"
        if not include_archived:
            sql += " WHERE archived = 0"
        sql += " ORDER BY sort_order, id"
        return [_row_to_field(r) for r in self.db.query(sql)]

    def get(self, field_id: int) -> FieldDef | None:
        r = self.db.query_one("SELECT * FROM field_def WHERE id = ?", (field_id,))
        return _row_to_field(r) if r else None

    def insert(self, f: FieldDef) -> int:
        cur = self.db.execute(
            "INSERT INTO field_def(name,type,options_json,aliases_json,role,group_name,"
            "sort_order,show_in_list,archived) VALUES (?,?,?,?,?,?,?,?,?)",
            (f.name, f.type, json.dumps(f.options, ensure_ascii=False),
             json.dumps(f.aliases, ensure_ascii=False), f.role, f.group_name,
             f.sort_order, int(f.show_in_list), int(f.archived)),
        )
        return cur.lastrowid

    def update(self, f: FieldDef) -> None:
        self.db.execute(
            "UPDATE field_def SET name=?,type=?,options_json=?,aliases_json=?,role=?,"
            "group_name=?,sort_order=?,show_in_list=?,archived=? WHERE id=?",
            (f.name, f.type, json.dumps(f.options, ensure_ascii=False),
             json.dumps(f.aliases, ensure_ascii=False), f.role, f.group_name,
             f.sort_order, int(f.show_in_list), int(f.archived), f.id),
        )

    def delete(self, field_id: int) -> None:
        """物理删除（会级联删除所有论文的该字段值）。仅供“永久删除已归档字段”使用。"""
        self.db.execute("DELETE FROM field_def WHERE id = ?", (field_id,))

    def max_sort_order(self) -> int:
        r = self.db.query_one("SELECT COALESCE(MAX(sort_order), 0) AS m FROM field_def")
        return r["m"]
