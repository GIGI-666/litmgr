"""导入服务（导入向导的后端）。

【作用】把用户选择的卡片 txt / PDF / 翻译 md / 附件批量导入系统，每篇论文一条记录。
【流程】
    1. build_plan(paths)：配对文件 -> 解析每张卡片 -> 检测重复 -> 汇总“未知标签”，返回 ImportPlan
       （只读，不改库；界面据此展示预览）
    2. 用户在向导里为每个未知标签做决定（映射到已有字段 / 新建字段 / 暂存待归类 / 并入上一字段 / 忽略）
    3. execute(plan, decisions)：创建论文、写字段值、复制文件进文献库、建索引
【设计要点】
    - “映射到已有字段”会把该标签记为字段别名，以后同样写法自动识别；
      “新建字段”会以标签原文作为字段名，同样自动记住。
    - 重复论文（arXiv 号或标题相同）默认跳过，用户可改成仍然导入。
    - 任何一篇出错不影响其他篇，错误汇总在 ImportResult.errors。
【依赖】importers.*、services.field_service / paper_service / file_service / pending_service /
    organize_service（只通过服务，不直接碰仓库）。
【被谁调用】ui.import_wizard。
【扩展点】新增导入来源（如 BibTeX）：写一个新 importer 产出同样的 ImportPlan 即可复用 execute。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from ..core.events import EventBus, Events
from ..core.models import (KIND_ATTACHMENT, KIND_CARD, KIND_PDF, KIND_TRANSLATION,
                           ROLE_ARXIV, ROLE_TITLE, ROLE_TITLE_EN, FieldDef)
from ..core.textutil import normalize_label
from ..importers.card_parser import ParsedCard, parse_card_text, read_text_file
from ..importers.file_pairing import PairGroup, pair_files
from .field_service import FieldService
from .file_service import FileService
from .organize_service import OrganizeService
from .paper_service import PaperService
from .pending_service import PendingService

_ARXIV_NUM = re.compile(r"(\d{4}\.\d{4,5})")

# 未知标签的处理方式
ACT_FIELD = "field"      # 映射到已有字段
ACT_NEW = "new"          # 新建字段
ACT_PENDING = "pending"  # 暂存到“待归类内容”
ACT_MERGE = "merge"      # 并入上一个字段的内容
ACT_IGNORE = "ignore"    # 忽略


@dataclass
class LabelDecision:
    action: str = ACT_PENDING
    field_id: int | None = None
    new_type: str = "longtext"
    new_name: str = ""


@dataclass
class UnknownLabel:
    """汇总各卡片中出现的未识别标签。"""

    key: str
    label: str
    numbered: bool
    guess: bool
    count: int = 0
    samples: list[str] = field(default_factory=list)

    def default_decision(self) -> LabelDecision:
        # 明确带编号的未知标签：默认暂存，等你归类。
        # 猜测型（未编号）：在多张卡片里反复出现 -> 基本是真字段，默认新建；
        #                    只出现一次 -> 可能只是正文里的一句话，默认并回上一字段（不丢内容）。
        if self.numbered or not self.guess:
            return LabelDecision(ACT_PENDING)
        return LabelDecision(ACT_NEW if self.count >= 2 else ACT_MERGE)


@dataclass
class ImportItem:
    group: PairGroup
    parsed: ParsedCard | None
    title: str
    duplicate_of: int | None = None
    action: str = "import"          # import / skip
    warnings: list[str] = field(default_factory=list)


@dataclass
class ImportPlan:
    items: list[ImportItem]
    unknown: list[UnknownLabel]


@dataclass
class ImportResult:
    created: list[int] = field(default_factory=list)
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


def _arxiv_of(text: str) -> str:
    m = _ARXIV_NUM.search(text or "")
    return m.group(1) if m else ""


class ImportService:
    def __init__(self, fields: FieldService, papers: PaperService, files: FileService,
                 pending: PendingService, organize: OrganizeService, events: EventBus) -> None:
        self.fields = fields
        self.papers = papers
        self.files = files
        self.pending = pending
        self.organize = organize
        self.events = events

    # ---------- 第一步：生成导入计划 ----------
    def build_plan(self, paths: list[Path]) -> ImportPlan:
        groups = pair_files([Path(p) for p in paths])
        lookup = self.fields.name_lookup()
        title_f = self.fields.by_role(ROLE_TITLE)
        title_en_f = self.fields.by_role(ROLE_TITLE_EN)
        arxiv_f = self.fields.by_role(ROLE_ARXIV)
        existing = self._existing_index(title_f, title_en_f, arxiv_f)

        items: list[ImportItem] = []
        unknown: dict[str, UnknownLabel] = {}
        for g in groups:
            parsed = None
            warnings: list[str] = []
            if g.card:
                try:
                    parsed = parse_card_text(read_text_file(g.card.path), lookup)
                except OSError as e:
                    warnings.append(f"卡片读取失败：{e}")
            if len(g.cards) > 1:
                warnings.append("同一论文有多个卡片文件，只导入第一个")
            if not g.card:
                warnings.append("没有找到论文卡片，将只导入文件")

            def text_of(f: FieldDef | None) -> str:
                return parsed.known_text(f.id) if (parsed and f) else ""

            title = (text_of(title_f) or text_of(title_en_f)).splitlines()[0:1]
            title_s = title[0] if title else g.title_hint
            item = ImportItem(g, parsed, title_s, warnings=warnings)
            only_card = g.card and not (g.pdfs or g.translations or g.attachments)
            if parsed is not None and only_card and not any(e.content.strip() for e in parsed.entries):
                item.action = "skip"
                warnings.append("卡片内容全为空（可能是空白模板），默认跳过")

            ax = _arxiv_of(text_of(arxiv_f)) or g.arxiv_hint
            dup = None
            if ax and ("arxiv", ax) in existing:
                dup = existing[("arxiv", ax)]
            elif ("title", normalize_label(title_s)) in existing and normalize_label(title_s):
                dup = existing[("title", normalize_label(title_s))]
            if dup:
                item.duplicate_of, item.action = dup, "skip"
                warnings.append(f"与已有论文重复（#{dup}），默认跳过")
            items.append(item)

            if parsed:
                for e in parsed.unknown_labels():
                    k = normalize_label(e.label)
                    u = unknown.setdefault(k, UnknownLabel(k, e.label, e.numbered, e.guess))
                    u.numbered = u.numbered or e.numbered
                    u.guess = u.guess and e.guess
                    u.count += 1
                    if len(u.samples) < 2:
                        u.samples.append(e.content[:80])
        return ImportPlan(items, sorted(unknown.values(), key=lambda u: -u.count))

    def _existing_index(self, title_f, title_en_f, arxiv_f) -> dict[tuple[str, str], int]:
        """已有论文的 arXiv 号/标题索引，用于重复检测。"""
        idx: dict[tuple[str, str], int] = {}
        for p in self.papers.list_all(include_archived=True):
            if arxiv_f and (a := _arxiv_of(p.text_of(arxiv_f.id))):
                idx.setdefault(("arxiv", a), p.id)
            for f in (title_f, title_en_f):
                if f and (t := p.text_of(f.id)):
                    idx.setdefault(("title", normalize_label(t.splitlines()[0])), p.id)
        return idx

    # ---------- 第二步：执行导入 ----------
    def execute(self, plan: ImportPlan, decisions: dict[str, LabelDecision] | None = None,
                collection_id: int | None = None) -> ImportResult:
        decisions = decisions or {}
        result = ImportResult()
        resolved = self._resolve_decisions(plan, decisions)

        title_f = self.fields.by_role(ROLE_TITLE)
        arxiv_f = self.fields.by_role(ROLE_ARXIV)
        for item in plan.items:
            if item.action != "import":
                result.skipped += 1
                continue
            created: list[int] = []   # 记下已创建的论文 id，失败时据此清理已复制的文件
            try:
                # 每篇论文一个事务：中途任何一步出错，数据库里不会留下这篇的半成品
                with self.papers.transaction():
                    pid = self._import_one(item, plan, decisions, resolved, title_f, arxiv_f,
                                           created)
                    if collection_id:
                        self.organize.add_to_collection([pid], collection_id, publish=False)
                result.created.append(pid)
            except Exception as e:  # noqa: BLE001 - 单篇失败不能拖垮整批
                for pid in created:
                    self.files.discard_dir(pid)
                result.errors.append(f"{item.title or item.group.title_hint}：{e}")
        self.events.publish(Events.LIBRARY_CHANGED)
        return result

    def _resolve_decisions(self, plan: ImportPlan,
                           decisions: dict[str, LabelDecision]) -> dict[str, int]:
        """把“映射/新建字段”类决定落实为 标签key -> 字段id；同时记住别名。"""
        resolved: dict[str, int] = {}
        for u in plan.unknown:
            d = decisions.get(u.key) or u.default_decision()
            if d.action == ACT_FIELD and d.field_id:
                self.fields.add_alias(d.field_id, u.label)
                resolved[u.key] = d.field_id
            elif d.action == ACT_NEW:
                name = (d.new_name or u.label).strip()
                existing = self.fields.name_lookup().get(normalize_label(name))
                if existing:
                    resolved[u.key] = existing
                else:
                    f = self.fields.add(name, d.new_type, aliases=[u.label] if name != u.label else [])
                    resolved[u.key] = f.id
        return resolved

    def _import_one(self, item: ImportItem, plan: ImportPlan,
                    decisions: dict[str, LabelDecision], resolved: dict[str, int],
                    title_f, arxiv_f, created: list[int]) -> int:
        values: dict[int, str] = {}
        pending: list[tuple[str, str]] = []
        last: tuple[str, int] | None = None   # ("field", fid) 或 ("pending", 下标)

        def put(fid: int, text: str) -> None:
            values[fid] = (values[fid] + "\n" + text).strip() if values.get(fid) else text

        for e in (item.parsed.entries if item.parsed else []):
            if e.field_id is not None:
                put(e.field_id, e.content)
                last = ("field", e.field_id)
                continue
            if not e.label:
                pending.append(("卡片开头内容", e.content))
                last = ("pending", len(pending) - 1)
                continue
            key = normalize_label(e.label)
            d = decisions.get(key) or next(
                (u.default_decision() for u in plan.unknown if u.key == key), LabelDecision())
            if key in resolved:
                put(resolved[key], e.content)
                last = ("field", resolved[key])
            elif d.action == ACT_IGNORE:
                continue
            elif d.action == ACT_MERGE and last:
                merged = f"{e.label}：{e.content}".strip("：")
                if last[0] == "field":
                    put(last[1], merged)
                else:
                    lbl, txt = pending[last[1]]
                    pending[last[1]] = (lbl, txt + "\n" + merged)
            else:
                pending.append((e.label, e.content))
                last = ("pending", len(pending) - 1)

        g = item.group
        if title_f and not values.get(title_f.id) and g.title_hint:
            values[title_f.id] = g.title_hint
        if arxiv_f and not values.get(arxiv_f.id) and g.arxiv_hint:
            values[arxiv_f.id] = g.arxiv_hint

        pid = self.papers.create({k: v for k, v in values.items() if v}, publish=False)
        created.append(pid)
        for label, content in pending:
            if content.strip():
                self.pending.add(pid, label, content)
        if g.card:
            self.files.add(pid, KIND_CARD, g.card.path, publish=False)
        for f in g.pdfs:
            self.files.add(pid, KIND_PDF, f.path, subtype=f.subtype, publish=False)
        for f in g.translations:
            self.files.add(pid, KIND_TRANSLATION, f.path, publish=False)
        for f in g.attachments:
            self.files.add(pid, KIND_ATTACHMENT, f.path, subtype=f.subtype, publish=False)
        return pid
