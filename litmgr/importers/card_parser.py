"""论文卡片 txt 解析器。

【作用】把一张“论文卡片”文本解析成 [(标签, 字段id或None, 内容)] 的列表。
【识别规则】
    1. 一行以“已知字段名或别名 + 冒号（中/英文）”开头 -> 开始该字段；后续行都算该字段内容，
       直到下一个字段标签出现（所以字段内容可以跨多行、可以含空行）。
    2. 兼容编号前缀：`(1)中文标题：`、`（22）我的疑问：`。
    3. 带编号前缀但名字未知的标签 -> 一定视为“未知字段”（numbered=True）。
    4. 没有编号、名字未知的行：只有当“标签短、含中文全角冒号、值也较短且标签不含标点”
       才猜测它是未知字段（guess=True），避免把正文里的“第一条路线：xxx”误判为字段。
       URL（https://…）不会被当成标签。
    5. 第一个标签之前的内容归入“卡片开头内容”（label 为空字符串）。
    6. 同一字段在一张卡片里重复出现：内容相同则忽略，不同则换行追加（不丢内容）。
【依赖】仅标准库 + core.textutil。known 查找表由调用方（services.field_service.name_lookup）提供。
【被谁调用】services.import_service；tests。
【扩展点】要支持新的卡片写法（如 Markdown 标题式字段），在 parse_card_text 增加一种标签识别规则。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..core.textutil import decode_text, normalize_label

# 编号前缀：必须带括号，避免把正文里的 “1、xxx” 误当编号
_NUM_PREFIX = re.compile(r"^\s*[\(（]\s*\d+\s*[\)）]\s*")
_COLON = re.compile(r"[：:]")
_LABEL_BAD_CHARS = re.compile(r"[，。,.;；、!！?？\s/]")  # 猜测型标签里不允许出现的字符（含空格）
GUESS_MAX_LABEL = 16
GUESS_MAX_VALUE = 60


def read_text_file(path) -> str:
    """读取 txt 文件，依次尝试 utf-8(含BOM)、gb18030，保证 Windows 常见编码都能读。"""
    with open(path, "rb") as f:
        return decode_text(f.read())


@dataclass
class CardEntry:
    """卡片里的一个字段块。"""

    label: str                    # 卡片里写的标签原文（开头内容为 ""）
    content: str                  # 字段内容（已去首尾空行）
    field_id: int | None = None   # 识别到的字段 id；None 表示未知
    numbered: bool = False        # 标签前有 (n) 编号
    guess: bool = False           # 是“猜测型”未知标签（未编号）


@dataclass
class ParsedCard:
    entries: list[CardEntry] = field(default_factory=list)

    def unknown_labels(self) -> list[CardEntry]:
        """所有未知标签块（不含卡片开头内容）。"""
        return [e for e in self.entries if e.field_id is None and e.label]

    def known_text(self, field_id: int) -> str:
        return "\n".join(e.content for e in self.entries if e.field_id == field_id)


def _split_label(line: str) -> tuple[str, str, bool, str] | None:
    """尝试把一行拆成 (标签, 行内剩余内容, 是否带编号, 所用冒号)。拆不出返回 None。"""
    m = _NUM_PREFIX.match(line)
    numbered = bool(m)
    body = line[m.end():] if m else line
    c = _COLON.search(body)
    if not c:
        return None
    label = body[:c.start()].strip()
    if not label:
        return None
    return label, body[c.end():].strip(), numbered, c.group()


def parse_card_text(text: str, known: dict[str, int]) -> ParsedCard:
    """解析卡片文本。known: 归一化标签 -> 字段 id。"""
    entries: list[CardEntry] = []
    cur: CardEntry | None = None
    buf: list[str] = []

    def flush() -> None:
        nonlocal cur, buf
        if cur is not None:
            cur.content = "\n".join(buf).strip("\n").strip()
            entries.append(cur)
        cur, buf = None, []

    text = text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    for line in text.split("\n"):
        parts = _split_label(line)
        new_entry: CardEntry | None = None
        if parts:
            label, rest, numbered, colon = parts
            fid = known.get(normalize_label(label))
            if fid is not None:
                new_entry = CardEntry(label, "", fid, numbered)
            elif numbered:
                new_entry = CardEntry(label, "", None, True)
            elif (colon == "：" and len(label) <= GUESS_MAX_LABEL
                  and not _LABEL_BAD_CHARS.search(label) and len(rest) <= GUESS_MAX_VALUE):
                new_entry = CardEntry(label, "", None, False, guess=True)
            if new_entry is not None:
                flush()
                cur = new_entry
                buf = [rest] if rest else []
                continue
        if cur is None and not line.strip():
            continue
        if cur is None:
            cur = CardEntry("", "")   # 卡片开头内容
        buf.append(line)
    flush()

    return ParsedCard(_merge_duplicates(entries))


def _merge_duplicates(entries: list[CardEntry]) -> list[CardEntry]:
    """同一已知字段重复出现：内容相同则忽略，不同则追加；其余原样保留顺序。"""
    out: list[CardEntry] = []
    seen: dict[int, CardEntry] = {}
    for e in entries:
        if e.field_id is not None and e.field_id in seen:
            first = seen[e.field_id]
            if e.content and normalize_label(e.content) != normalize_label(first.content):
                first.content = (first.content + "\n" + e.content).strip()
            continue
        if e.field_id is not None:
            seen[e.field_id] = e
        if e.label == "" and not e.content:
            continue
        out.append(e)
    return out
