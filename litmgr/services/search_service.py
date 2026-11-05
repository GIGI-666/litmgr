"""检索服务。

【作用】根据 SearchQuery 找出符合条件的论文并排序。主界面的搜索框、过滤器、
    侧栏（标签/分组/保存的检索）全部通过它完成。
【能力】
    - 文本搜索：空格分隔多个词，必须全部命中（AND）；可限定在某些字段内；
      可选同时搜索翻译正文与笔记
    - 字段条件：按字段类型提供包含/等于/为空/大于/小于/含标签等
    - 标签、分组、阅读状态、最低星级过滤
    - 排序：id / 更新时间 / 标题 / 阅读状态 / 星级 / 任意字段
【依赖】core.query（SearchQuery）、core.field_types（条件判断）；
    storage.search_repo / organize_repo；services.field_service / paper_service。
【被谁调用】ui.main_window / ui.paper_table。
【扩展点】新增过滤维度：在 core.query.SearchQuery 加字段，并在 run() 里加一步过滤；
    新增/修改某类型字段的比较规则：改对应 FieldType 的 matches，不用动这里。
"""

from __future__ import annotations

from ..core.field_types import get_type
from ..core.models import FieldDef, Paper
from ..core.query import Condition, SearchQuery
from ..storage.organize_repo import OrganizeRepo
from ..storage.search_repo import SearchRepo
from .field_service import FieldService
from .paper_service import PaperService


class SearchService:
    def __init__(self, search_repo: SearchRepo, organize_repo: OrganizeRepo,
                 fields: FieldService, papers: PaperService) -> None:
        self.search = search_repo
        self.organize = organize_repo
        self.fields = fields
        self.papers = papers

    def run(self, q: SearchQuery | None = None) -> list[Paper]:
        q = q or SearchQuery()
        active = {f.id: f for f in self.fields.list()}
        papers = self.papers.list_all(include_archived=q.include_archived)

        # 1) 文本搜索：每个词都必须命中（交集）
        tokens = q.text.split()
        if tokens:
            if q.scope_field_ids is None:
                scope = list(active)
            else:
                scope = [fid for fid in q.scope_field_ids if fid in active]
            ids: set[int] | None = None
            for tok in tokens:
                hit = self.search.paper_ids_matching(
                    tok, scope, include_files=q.include_fulltext,
                    include_notes=q.include_fulltext)
                ids = hit if ids is None else ids & hit
            papers = [p for p in papers if p.id in (ids or set())]

        # 2) 标签 / 分组
        for tid in q.tag_ids:
            ids = self.organize.paper_ids_with_tag(tid)
            papers = [p for p in papers if p.id in ids]
        if q.collection_id:
            ids = self.organize.paper_ids_in_collection(q.collection_id)
            papers = [p for p in papers if p.id in ids]

        # 3) 状态 / 星级
        if q.read_status:
            papers = [p for p in papers if p.read_status == q.read_status]
        if q.min_rating:
            papers = [p for p in papers if p.rating >= q.min_rating]

        # 4) 字段条件
        for c in q.conditions:
            f = active.get(c.field_id)
            if f:
                papers = [p for p in papers if self._match(p, f, c)]

        return self._sort(papers, q, active)

    # ---------- 字段条件判断 ----------
    @staticmethod
    def _match(p: Paper, f: FieldDef, c: Condition) -> bool:
        """各操作符的具体判断规则由字段类型自己负责（FieldType.matches）。"""
        val = p.values.get(f.id)
        return get_type(f.type).matches(
            c.op, val.text if val else "", val.json if val else None, c.value)

    # ---------- 排序 ----------
    @staticmethod
    def _sort(papers: list[Paper], q: SearchQuery, active: dict[int, FieldDef]) -> list[Paper]:
        key = q.sort_key
        if key.startswith("f:"):
            f = active.get(int(key[2:]))
            if f:
                ft = get_type(f.type)
                filled = [p for p in papers if p.text_of(f.id).strip()]
                empty = [p for p in papers if not p.text_of(f.id).strip()]
                filled.sort(key=lambda p: ft.sort_key(p.values[f.id].text, p.values[f.id].json),
                            reverse=q.sort_desc)
                return filled + empty   # 空值始终排在最后
        keyfn = {
            "id": lambda p: p.id,
            "updated": lambda p: p.updated_at,
            "title": lambda p: p.title.casefold(),
            "status": lambda p: p.read_status,
            "rating": lambda p: p.rating,
        }.get(key, lambda p: p.id)
        return sorted(papers, key=keyfn, reverse=q.sort_desc)
