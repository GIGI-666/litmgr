"""全文检索索引仓库（search_index 虚拟表）。

【作用】维护并查询 FTS5 全文索引，覆盖：字段值、翻译文件正文、笔记。
【设计要点】
    - 使用 trigram 分词，天然支持中文子串检索（查询词需 >= 3 个字符）；
      1~2 个字符的查询词自动回退到 LIKE。
    - 手工指定 rowid 以便按“论文+字段/文件/笔记”精确删除，避免全表扫描：
        字段行  rowid = paper_id * 1_000_000 + field_id        （source='field'）
        文件行  rowid = -file_id                                （source='file'）
        笔记行  rowid = -(10**12 + paper_id)                    （source='note'）
【依赖】storage.database。
【被谁调用】services.paper_service / search_service / note_service / import_service。
【扩展点】要索引新的内容来源，约定新的 source 与 rowid 规则即可。
"""

from __future__ import annotations

from typing import Iterable

from .database import Database

_FIELD_ID_LIMIT = 1_000_000
_NOTE_BASE = 10**12


def _field_rowid(paper_id: int, field_id: int) -> int:
    return paper_id * _FIELD_ID_LIMIT + field_id


class SearchRepo:
    def __init__(self, db: Database) -> None:
        self.db = db

    # ---------- 索引维护 ----------
    def index_field(self, paper_id: int, field_id: int, text: str) -> None:
        rid = _field_rowid(paper_id, field_id)
        self.db.execute("DELETE FROM search_index WHERE rowid=?", (rid,))
        if text.strip():
            self.db.execute(
                "INSERT INTO search_index(rowid,paper_id,field_id,source,content) "
                "VALUES (?,?,?,?,?)", (rid, paper_id, field_id, "field", text))

    def remove_field(self, paper_id: int, field_id: int) -> None:
        self.db.execute("DELETE FROM search_index WHERE rowid=?",
                        (_field_rowid(paper_id, field_id),))

    def remove_field_everywhere(self, field_id: int, paper_ids: Iterable[int]) -> None:
        for pid in paper_ids:
            self.remove_field(pid, field_id)

    def index_file(self, paper_id: int, file_id: int, text: str) -> None:
        self.db.execute("DELETE FROM search_index WHERE rowid=?", (-file_id,))
        if text.strip():
            self.db.execute(
                "INSERT INTO search_index(rowid,paper_id,field_id,source,content) "
                "VALUES (?,?,NULL,'file',?)", (-file_id, paper_id, text))

    def remove_file(self, file_id: int) -> None:
        self.db.execute("DELETE FROM search_index WHERE rowid=?", (-file_id,))

    def index_notes(self, paper_id: int, text: str) -> None:
        rid = -(_NOTE_BASE + paper_id)
        self.db.execute("DELETE FROM search_index WHERE rowid=?", (rid,))
        if text.strip():
            self.db.execute(
                "INSERT INTO search_index(rowid,paper_id,field_id,source,content) "
                "VALUES (?,?,NULL,'note',?)", (rid, paper_id, text))

    def clear(self) -> None:
        self.db.execute("DELETE FROM search_index")

    # ---------- 查询 ----------
    def paper_ids_matching(self, token: str, field_ids: list[int] | None = None,
                           include_files: bool = True, include_notes: bool = True) -> set[int]:
        """返回在指定范围内包含 token 的论文 id 集合（大小写不敏感的子串匹配）。

        field_ids=None 表示所有字段；include_files / include_notes 控制是否搜翻译正文与笔记。
        """
        scopes: list[str] = []
        params: list = []
        if field_ids is None:
            scopes.append("source='field'")
        elif field_ids:
            scopes.append(f"(source='field' AND field_id IN ({','.join('?' * len(field_ids))}))")
            params.extend(field_ids)
        if include_files:
            scopes.append("source='file'")
        if include_notes:
            scopes.append("source='note'")
        if not scopes:
            return set()
        scope_sql = "(" + " OR ".join(scopes) + ")"

        if len(token) >= 3:
            phrase = '"' + token.replace('"', '""') + '"'
            sql = f"SELECT DISTINCT paper_id FROM search_index WHERE search_index MATCH ? AND {scope_sql}"
            params = [phrase] + params
        else:
            like = "%" + token.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
            sql = (f"SELECT DISTINCT paper_id FROM search_index "
                   f"WHERE content LIKE ? ESCAPE '\\' AND {scope_sql}")
            params = [like] + params
        return {r["paper_id"] for r in self.db.query(sql, params)}
