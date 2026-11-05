"""检索条件的数据结构。

【作用】描述“要找什么样的论文”：搜索词、字段条件、标签/分组/状态/星级、排序方式。
    只是纯数据（可序列化为 dict，用于“保存的检索”），不含任何查询逻辑，
    所以放在 core 层：services 里的检索/整理服务、ui 里的过滤器都能依赖它而不互相依赖。
【依赖】仅标准库。
【被谁调用】services.search_service / organize_service；ui.main_window / filter_dialog。
【扩展点】新增过滤维度：在 SearchQuery 加字段，并在 SearchService.run() 里加一步过滤；
    from_dict 会忽略未知键、缺省键取默认值，所以旧的“保存的检索”不会因新增字段而失效。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class Condition:
    """一条字段条件：字段 + 操作（见 core.field_types 的 OP_*）+ 比较值。"""
    field_id: int
    op: str
    value: str = ""


@dataclass
class SearchQuery:
    text: str = ""
    scope_field_ids: list[int] | None = None   # None = 所有字段
    include_fulltext: bool = True              # 同时搜索翻译正文、笔记
    conditions: list[Condition] = field(default_factory=list)
    tag_ids: list[int] = field(default_factory=list)
    collection_id: int | None = None
    read_status: str | None = None
    min_rating: int = 0
    include_archived: bool = False
    sort_key: str = "id"                       # id/updated/title/status/rating/f:<字段id>
    sort_desc: bool = True

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "SearchQuery":
        d = dict(d)
        d["conditions"] = [Condition(**c) for c in d.get("conditions", [])]
        known = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**known)

    def copy(self) -> "SearchQuery":
        """深拷贝（条件列表等不与原对象共享）。"""
        return SearchQuery.from_dict(self.to_dict())
