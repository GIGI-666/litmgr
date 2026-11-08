"""字段定义仓库（field_def 表）。

【作用】读写“字段定义”及独立的字段分组；空分组也可持久保存。
【职责】只做数据读写；字段名查重、类型转换等业务规则在 services.field_service。
【依赖】storage.database；core.models。
【被谁调用】services.field_service、services.paper_service、importers（通过服务）。
【扩展点】字段及分组的 SQL 操作集中于本仓库，跨记录变更由服务层组织事务。
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

    def groups(self) -> list[str]:
        """按建立顺序列出分组，包含空分组及只有已归档字段的分组。"""
        return [r["name"] for r in self.db.query(
            "SELECT name FROM field_group ORDER BY sort_order, rowid")]

    def ensure_group(self, name: str) -> None:
        """确保具名分组存在；空字符串表示字段未分组，不建立记录。"""
        if name:
            self.db.execute(
                "INSERT OR IGNORE INTO field_group(name, sort_order) "
                "VALUES (?, (SELECT COALESCE(MAX(sort_order), -1) + 1 FROM field_group))",
                (name,))

    def rename_group(self, old_name: str, new_name: str) -> None:
        """改组名并同步所有字段（含已归档字段）；由调用方包裹事务。"""
        self.db.execute("UPDATE field_group SET name = ? WHERE name = ?", (new_name, old_name))
        self.db.execute("UPDATE field_def SET group_name = ? WHERE group_name = ?",
                        (new_name, old_name))

    def delete_group(self, name: str) -> None:
        """移除分组并把组内字段设为未分组，保留字段和值；由调用方包裹事务。"""
        self.db.execute("UPDATE field_def SET group_name = '' WHERE group_name = ?", (name,))
        self.db.execute("DELETE FROM field_group WHERE name = ?", (name,))
