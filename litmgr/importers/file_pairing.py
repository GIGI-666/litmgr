"""导入文件的分类与配对。

【作用】给定一批文件（或一个文件夹），自动判断每个文件是“卡片 / PDF / 翻译 / 附件”，
    并把属于同一篇论文的文件分到同一组（PairGroup）。
【规则（基于用户真实命名习惯）】
    文件名形如：`{论文标题}{arXiv号或年月}{后缀标记}.扩展名`
    - 后缀标记：论文卡片、翻译、补充材料、附录、论文详细内容
    - .txt -> 卡片；.md -> 翻译；.pdf -> PDF（带“补充材料/附录”则标注子类型）；
      其他扩展名（.docx 等）-> 附件
    - 配对键 = 去掉后缀标记与末尾编号（`2606.23344v1`、`2406`、`2005` 之类）后的标题；
      补充材料常与正文的编号不同（如 2606.23344v1 与 2609），所以编号不参与配对。
    - 标题键不完全相同时，用相似度（>=0.88）兜底合并。
【依赖】仅标准库。
【被谁调用】services.import_service。
【扩展点】新的命名习惯：在 SUFFIX_MARKERS / classify 中增加规则。
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from pathlib import Path

from ..core.models import (KIND_ATTACHMENT, KIND_CARD, KIND_PDF, KIND_TRANSLATION,
                           SUBTYPE_APPENDIX, SUBTYPE_MAIN, SUBTYPE_SUPPLEMENT)

# 后缀标记 -> (文件种类覆盖, PDF 子类型)；按长度降序匹配
SUFFIX_MARKERS = ["论文详细内容", "论文卡片", "补充材料", "附录", "翻译"]

# 末尾的 arXiv 号/年月号：2606.23344v1、2410.21169v5、2406、2005、1712
_TRAILING_ID = re.compile(r"(?:\d{4}\.\d{4,5}|\d{4})(?:v\d+)?$")
_ARXIV_IN_NAME = re.compile(r"(\d{4}\.\d{4,5})(?:v\d+)?")
_PUNCT = re.compile(r"[\s\-_:：，,。.（）()]+")
SIMILARITY = 0.88


@dataclass
class FileInfo:
    path: Path
    kind: str
    subtype: str = ""
    title_key: str = ""     # 用于配对的归一化标题
    title_hint: str = ""    # 可读标题（用于无卡片时给论文起名）
    arxiv_hint: str = ""    # 从文件名里读到的 arXiv 号（如有）


@dataclass
class PairGroup:
    """属于同一篇论文的一组文件。"""

    key: str
    fuzzy: bool = False     # 有文件是按“标题相似”而不是“标题相同”并进来的（提醒用户核对）
    title_hint: str = ""
    arxiv_hint: str = ""
    cards: list[FileInfo] = field(default_factory=list)
    pdfs: list[FileInfo] = field(default_factory=list)
    translations: list[FileInfo] = field(default_factory=list)
    attachments: list[FileInfo] = field(default_factory=list)

    @property
    def card(self) -> FileInfo | None:
        return self.cards[0] if self.cards else None


def _norm_key(s: str) -> str:
    return _PUNCT.sub("", s).casefold()


def classify(path: Path) -> FileInfo:
    """判断单个文件的种类，并抽取配对键。"""
    stem = path.stem
    ext = path.suffix.lower()
    marker = ""
    changed = True
    while changed:  # 可能叠加多个标记，如 “…补充材料” 前还有别的
        changed = False
        for m in SUFFIX_MARKERS:
            if stem.endswith(m):
                marker = marker or m
                stem = stem[: -len(m)].rstrip(" _-")
                changed = True
    arxiv = ""
    if m := _ARXIV_IN_NAME.search(stem):
        arxiv = m.group(1)
    title = _TRAILING_ID.sub("", stem).rstrip(" _-")
    if ext == ".txt":
        kind = KIND_CARD
    elif ext in (".md", ".markdown"):
        kind = KIND_TRANSLATION
    elif ext == ".pdf":
        kind = KIND_PDF
    else:
        kind = KIND_ATTACHMENT
    subtype = ""
    if kind == KIND_PDF:
        subtype = {"补充材料": SUBTYPE_SUPPLEMENT, "附录": SUBTYPE_APPENDIX}.get(marker, SUBTYPE_MAIN)
    elif kind == KIND_ATTACHMENT:
        subtype = marker or ""
    return FileInfo(path=path, kind=kind, subtype=subtype, title_key=_norm_key(title),
                    title_hint=title, arxiv_hint=arxiv)


def collect_files(paths: list[Path]) -> list[Path]:
    """展开用户选择的文件/文件夹（文件夹递归，忽略隐藏文件与 .obsidian 等点目录）。"""
    out: list[Path] = []
    seen: set[Path] = set()   # 同一文件可能同时被“文件夹”和“文件”选中，只保留一份

    def add(f: Path) -> None:
        key = f.resolve()
        if key not in seen:
            seen.add(key)
            out.append(f)

    for p in paths:
        p = Path(p)
        if p.is_dir():
            for f in sorted(p.rglob("*")):
                if f.is_file() and not any(part.startswith(".") for part in f.relative_to(p).parts):
                    if f.stat().st_size > 0:
                        add(f)
        elif p.is_file():
            add(p)
    return out


def pair_files(paths: list[Path]) -> list[PairGroup]:
    """把文件配对成论文组。"""
    groups: dict[str, PairGroup] = {}
    for f in collect_files(paths):
        info = classify(f)
        if not info.title_key:
            info.title_key = _norm_key(f.stem)
            info.title_hint = f.stem
        key = _find_group_key(groups, info.title_key)
        g = groups.setdefault(key, PairGroup(key=key))
        if key != info.title_key:
            g.fuzzy = True
        if not g.title_hint or len(info.title_hint) > len(g.title_hint):
            g.title_hint = info.title_hint
        g.arxiv_hint = g.arxiv_hint or info.arxiv_hint
        {KIND_CARD: g.cards, KIND_PDF: g.pdfs, KIND_TRANSLATION: g.translations,
         KIND_ATTACHMENT: g.attachments}[info.kind].append(info)
    return list(groups.values())


def _find_group_key(groups: dict[str, PairGroup], key: str) -> str:
    """精确命中，否则按相似度找最像的已有组，都不像则自成新组。"""
    if key in groups:
        return key
    best, best_ratio = key, 0.0
    sm = difflib.SequenceMatcher(None)
    sm.set_seq2(key)          # seq2 的预处理只做一次，对每个已有分组复用
    for k in groups:
        sm.set_seq1(k)
        # 先用便宜的上界过滤：长度悬殊或字符组成差太多的，不可能达到阈值
        if sm.real_quick_ratio() < SIMILARITY or sm.quick_ratio() < SIMILARITY:
            continue
        r = sm.ratio()
        if r > best_ratio:
            best, best_ratio = k, r
    return best if best_ratio >= SIMILARITY else key
