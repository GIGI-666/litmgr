"""论文对比服务。

【作用】为“对比窗口”准备数据：选 N 篇论文 × M 个字段，生成对照表，并标出每个字段
    在这些论文之间是否一致。
【依赖】services.paper_service / field_service；core.field_types。
【被谁调用】ui.compare_window；services.export_service（导出对比表）。
【扩展点】要增加“高亮差异片段”等分析，在 CompareRow 上加属性并在 build 中计算。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..core.field_types import get_type
from ..core.models import FieldDef, Paper
from .field_service import FieldService
from .paper_service import PaperService


@dataclass
class CompareRow:
    field: FieldDef
    cells: list[str]           # 与 CompareTable.papers 一一对应
    all_same: bool             # 所有论文该字段的值是否一致（含全部为空）
    all_empty: bool


@dataclass
class CompareTable:
    papers: list[Paper]
    rows: list[CompareRow] = field(default_factory=list)

    def only_different(self) -> "CompareTable":
        return CompareTable(self.papers, [r for r in self.rows if not r.all_same])

    def hide_empty(self) -> "CompareTable":
        return CompareTable(self.papers, [r for r in self.rows if not r.all_empty])


class CompareService:
    def __init__(self, papers: PaperService, fields: FieldService) -> None:
        self.papers = papers
        self.fields = fields

    def build(self, paper_ids: list[int], field_ids: list[int] | None = None) -> CompareTable:
        """field_ids 为 None 表示所有（未归档）字段，按字段顺序排列。"""
        papers = self.papers.get_many(paper_ids)
        all_fields = self.fields.list()
        if field_ids is not None:
            by_id = {f.id: f for f in all_fields}
            all_fields = [by_id[i] for i in field_ids if i in by_id]
        table = CompareTable(papers)
        for f in all_fields:
            ft = get_type(f.type)
            cells, keys = [], []
            for p in papers:
                v = p.values.get(f.id)
                cells.append(v.text if v else "")
                keys.append(ft.compare_text(v.text, v.json) if v else "")
            table.rows.append(CompareRow(f, cells, len(set(keys)) <= 1,
                                         all(not k for k in keys)))
        return table
