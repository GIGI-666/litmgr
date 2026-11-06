"""导出服务。

【作用】把库里的数据导出为外部文件：
    - 论文卡片 txt（与导入格式一致，可再导入；每篇论文一个文件）
    - CSV（所选论文 × 所选字段，Excel 可直接打开）
    - 对比表（CSV / Markdown）
【机制】导出器通过注册表 exporters 接入：名字 -> 函数(paper_ids, field_ids, target) -> 生成的文件列表。
    新增导出格式 = 写一个函数并 exporters.register，不用改界面外的代码。
【依赖】services.paper_service / field_service / compare_service；core.registry。
【被谁调用】ui 的“导出”菜单、对比窗口。
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Callable

from ..core.registry import Registry
from ..core.textutil import safe_filename
from .compare_service import CompareTable
from .field_service import FieldService
from .paper_service import PaperService

Exporter = Callable[[list[int], list[int] | None, Path], list[Path]]


class ExportService:
    def __init__(self, papers: PaperService, fields: FieldService) -> None:
        self.papers = papers
        self.fields = fields
        self.exporters: Registry[Exporter] = Registry("导出器")
        self.exporters.register("txt", self._export_txt)
        self.exporters.register("csv", self._export_csv)

    def export(self, fmt: str, paper_ids: list[int], target: Path,
               field_ids: list[int] | None = None) -> list[Path]:
        """target：txt 为目标文件夹；csv 为目标文件。"""
        return self.exporters.get(fmt)(paper_ids, field_ids, Path(target))

    # ---------- 内置导出器 ----------
    def _select_fields(self, field_ids):
        fs = self.fields.list()
        if field_ids is not None:
            by_id = {f.id: f for f in fs}
            fs = [by_id[i] for i in field_ids if i in by_id]
        return fs

    def _export_txt(self, paper_ids, field_ids, target: Path) -> list[Path]:
        target.mkdir(parents=True, exist_ok=True)
        fields = self._select_fields(field_ids)
        out: list[Path] = []
        for p in self.papers.get_many(paper_ids):
            lines = []
            for f in fields:
                lines.append(f"{f.name}：{p.text_of(f.id)}")
            path = target / f"{safe_filename(p.title)}论文卡片.txt"
            n = 2
            while path.exists():
                path = target / f"{safe_filename(p.title)}论文卡片_{n}.txt"
                n += 1
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            out.append(path)
        return out

    def _export_csv(self, paper_ids, field_ids, target: Path) -> list[Path]:
        fields = self._select_fields(field_ids)
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.writer(fh)
            w.writerow(["ID", "标题", "阅读状态", "星级"] + [f.name for f in fields])
            for p in self.papers.get_many(paper_ids):
                w.writerow([p.id, p.title, p.read_status, p.rating] +
                           [p.text_of(f.id) for f in fields])
        return [target]

    # ---------- 对比表导出 ----------
    @staticmethod
    def export_compare(table: CompareTable, target: Path, fmt: str = "csv") -> Path:
        target = Path(target)
        titles = [p.title for p in table.papers]
        if fmt == "md":
            titles = [t.replace("|", "\\|") for t in titles]   # 标题里的竖线会破坏表格
            lines = ["| 字段 | " + " | ".join(titles) + " |",
                     "|---|" + "---|" * len(titles)]
            for r in table.rows:
                cells = [c.replace("\n", "<br>").replace("|", "\\|") for c in r.cells]
                lines.append(f"| {r.field.name} | " + " | ".join(cells) + " |")
            target.write_text("\n".join(lines) + "\n", encoding="utf-8")
        else:
            with open(target, "w", newline="", encoding="utf-8-sig") as fh:
                w = csv.writer(fh)
                w.writerow(["字段"] + titles)
                for r in table.rows:
                    w.writerow([r.field.name] + r.cells)
        return target
