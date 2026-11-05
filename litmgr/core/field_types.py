"""字段类型体系。

【作用】定义“字段值如何解析、规范化、排序、过滤”，每种类型是一个 FieldType 子类，
    通过注册表 FIELD_TYPES 接入。新增类型 = 新增一个子类并 register，其他代码不用改。
【核心约定】
    - 任何字段值都以 (value_text, value_json) 存储：
      value_text 是统一的文本形态，用于显示、全文检索、导出；
      value_json 是结构化形态（标签数组、数字、星级等），可为 None。
    - 解析永远“不丢数据”：无法按类型解析时保留原文本，value_json 置 None。
      因此字段类型可以随时切换，只需用新类型重新解析 value_text。
【依赖】仅标准库 + core.registry。
【被谁调用】services.paper_service / field_service（写入时规范化）、
    ui.field_widgets（选择编辑控件）、services.search_service（过滤、排序）。
【扩展点】新增类型：继承 FieldType、实现 parse，再 FIELD_TYPES.register(...)；
    界面控件在 ui.field_widgets 的控件注册表里同名注册即可。
"""

from __future__ import annotations

import re
from typing import Any

from .registry import Registry
from .textutil import URL_RE

# 所有类型都支持的过滤操作，界面据此生成过滤条件菜单
OP_CONTAINS = "contains"
OP_EQUALS = "equals"
OP_EMPTY = "empty"
OP_NOT_EMPTY = "not_empty"
OP_GT = "gt"
OP_LT = "lt"
OP_HAS = "has"  # 标签类：包含某个标签

OP_LABELS = {
    OP_CONTAINS: "包含",
    OP_EQUALS: "等于",
    OP_EMPTY: "为空",
    OP_NOT_EMPTY: "不为空",
    OP_GT: "大于/晚于",
    OP_LT: "小于/早于",
    OP_HAS: "含有标签",
}


class FieldType:
    """字段类型基类。"""

    name = "text"
    label = "单行文本"
    multiline = False            # 编辑时是否使用多行控件
    ops = (OP_CONTAINS, OP_EQUALS, OP_EMPTY, OP_NOT_EMPTY)

    def parse(self, raw: str | None, options: list[str] | None = None) -> tuple[str, Any]:
        """把用户输入/导入的原始文本解析为 (value_text, value_json)。"""
        text = (raw or "").strip()
        return text, None

    def sort_key(self, value_text: str, value_json: Any) -> Any:
        """排序键：空值总是排在最后（由调用方处理），这里只给非空值的键。"""
        return value_text.casefold()

    def compare_text(self, value_text: str, value_json: Any) -> str:
        """对比窗口里用于判断“两篇论文该字段是否相同”的规范文本。"""
        return " ".join(value_text.split()).casefold()

    def matches(self, op: str, value_text: str, value_json: Any, operand: str) -> bool:
        """字段条件判断：该字段的值是否满足“op operand”。

        基类实现通用操作（为空/不为空/包含/等于/大于/小于）；类型有特殊规则就覆盖
        （如标签的“含有标签”、数字的数值比较）。不认识的操作返回 True（等于不过滤）。
        """
        text = value_text.strip()
        if op == OP_EMPTY:
            return not text
        if op == OP_NOT_EMPTY:
            return bool(text)
        if op == OP_CONTAINS:
            return operand.strip().casefold() in text.casefold()
        if op == OP_EQUALS:
            return self.compare_text(text, value_json) == self.compare_text(operand, None)
        if op in (OP_GT, OP_LT):
            return self._order(op, text, operand)
        return True

    def _order(self, op: str, text: str, operand: str) -> bool:
        """大于/小于：默认按规范化后的文本比较（日期规范化后可直接按字典序）。"""
        if not text:
            return False
        norm, _ = self.parse(operand)
        return text > norm if op == OP_GT else text < norm


class TextType(FieldType):
    name = "text"
    label = "单行文本"


class LongTextType(FieldType):
    name = "longtext"
    label = "长文本"
    multiline = True


class SelectType(FieldType):
    """单选。options 只是候选项（用于下拉提示），允许输入候选项之外的值，避免导入时丢数据。"""

    name = "select"
    label = "单选"
    ops = (OP_EQUALS, OP_CONTAINS, OP_EMPTY, OP_NOT_EMPTY)


_TAG_SPLIT = re.compile(r"[,，、;；\n]+")


class TagsType(FieldType):
    """多标签。输入用逗号/顿号/分号/换行分隔；去重并保持顺序。"""

    name = "tags"
    label = "多标签"
    ops = (OP_HAS, OP_CONTAINS, OP_EMPTY, OP_NOT_EMPTY)

    def parse(self, raw, options=None):
        items: list[str] = []
        for part in _TAG_SPLIT.split(raw or ""):
            part = part.strip()
            if part and part not in items:
                items.append(part)
        return "、".join(items), (items or None)

    def matches(self, op, value_text, value_json, operand):
        if op == OP_HAS:
            items = value_json if isinstance(value_json, list) else [value_text.strip()]
            needle = operand.strip().casefold()
            return any(needle == str(i).casefold() for i in items if i)
        return super().matches(op, value_text, value_json, operand)


def _to_float(s: str) -> float | None:
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


class _NumericOrderMixin:
    """数字/星级：大于、小于按数值比较（任一边不是数字时退回文本比较）。"""

    def _order(self, op: str, text: str, operand: str) -> bool:
        if not text:
            return False
        a, b = _to_float(text), _to_float(operand)
        if a is not None and b is not None:
            return a > b if op == OP_GT else a < b
        return FieldType._order(self, op, text, operand)


class NumberType(_NumericOrderMixin, FieldType):
    name = "number"
    label = "数字"
    ops = (OP_EQUALS, OP_GT, OP_LT, OP_EMPTY, OP_NOT_EMPTY)

    def parse(self, raw, options=None):
        text = (raw or "").strip()
        try:
            return text, float(text)
        except ValueError:
            return text, None  # 如 “10+5”，保留原文

    def sort_key(self, value_text, value_json):
        return value_json if value_json is not None else float("inf")


_DATE_FULL = re.compile(r"^(\d{4})\s*[-./年]\s*(\d{1,2})\s*[-./月]\s*(\d{1,2})\s*日?$")
_DATE_MONTH = re.compile(r"^(\d{4})\s*[-./年]\s*(\d{1,2})\s*月?$")
_DATE_YEAR = re.compile(r"^(\d{4})\s*年?$")


class DateType(FieldType):
    """日期。能识别的规范化为 YYYY-MM-DD / YYYY-MM / YYYY（便于按文本排序），否则保留原文。"""

    name = "date"
    label = "日期"
    ops = (OP_EQUALS, OP_GT, OP_LT, OP_CONTAINS, OP_EMPTY, OP_NOT_EMPTY)

    def parse(self, raw, options=None):
        text = (raw or "").strip()
        if m := _DATE_FULL.match(text):
            y, mo, d = (int(x) for x in m.groups())
            if 1 <= mo <= 12 and 1 <= d <= 31:
                norm = f"{y:04d}-{mo:02d}-{d:02d}"
                return norm, norm
        elif m := _DATE_MONTH.match(text):
            y, mo = (int(x) for x in m.groups())
            if 1 <= mo <= 12:
                norm = f"{y:04d}-{mo:02d}"
                return norm, norm
        elif (m := _DATE_YEAR.match(text)) and 1900 <= int(m.group(1)) <= 2100:
            norm = m.group(1)   # 4 位数字仅在合理年份范围内才当作年份（避免把 2410 这种年月号当年份）
            return norm, norm
        return text, None

    def sort_key(self, value_text, value_json):
        return value_json if value_json else "9999-" + value_text


class RatingType(_NumericOrderMixin, FieldType):
    name = "rating"
    label = "星级(0-5)"
    ops = (OP_EQUALS, OP_GT, OP_LT, OP_EMPTY, OP_NOT_EMPTY)

    def parse(self, raw, options=None):
        text = (raw or "").strip()
        try:
            n = max(0, min(5, int(float(text))))
        except ValueError:
            return text, None
        return (str(n), n) if text != "" else ("", None)

    def sort_key(self, value_text, value_json):
        return value_json if value_json is not None else -1


class UrlType(FieldType):
    """链接（可多行，多个链接）。value_json 存提取到的 URL 列表，界面可一键打开。"""

    name = "url"
    label = "链接"
    multiline = True

    def parse(self, raw, options=None):
        text = (raw or "").strip()
        urls = URL_RE.findall(text)
        return text, (urls or None)


FIELD_TYPES: Registry[FieldType] = Registry("字段类型")
for _t in (TextType(), LongTextType(), SelectType(), TagsType(), NumberType(),
           DateType(), RatingType(), UrlType()):
    FIELD_TYPES.register(_t.name, _t)


def get_type(name: str) -> FieldType:
    """按名取字段类型；未知类型回退为长文本，保证旧数据永远能显示。"""
    return FIELD_TYPES.get(name) if name in FIELD_TYPES else FIELD_TYPES.get("longtext")
