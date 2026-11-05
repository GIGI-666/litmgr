"""文本小工具：全工程共用的几个纯函数，避免在各模块里各写一份。

【作用】
    - normalize_label：名称归一化（去空白、转小写），字段名/别名/卡片标签的匹配与查重都用它
    - safe_filename：把任意文本变成可作 Windows 文件名的字符串
    - decode_text：把字节解码成文本，依次尝试 utf-8(含 BOM)、gb18030，保证 Windows 常见编码都能读
    - URL_RE：从文本里提取 http(s) 链接的正则
【依赖】仅标准库。
【被谁调用】importers.card_parser、storage.library_fs、services.field_service /
    export_service、core.field_types、ui.field_widgets。
"""

from __future__ import annotations

import re

_WS = re.compile(r"\s+")
_BAD_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|\r\n\t]+')

# 链接结束于空白或中英文常见分隔符，避免把后面的标点吞进去
URL_RE = re.compile(r"https?://[^\s，,；;）)]+")


def normalize_label(s: str) -> str:
    """名称归一化：去掉所有空白并转小写，用于字段名/别名/卡片标签的匹配与查重。"""
    return _WS.sub("", s or "").casefold()


def safe_filename(s: str, limit: int = 80, default: str = "未命名") -> str:
    """去掉文件名里的非法字符（换成下划线），截断到 limit 个字符；结果为空时用 default。"""
    return _BAD_FILENAME_CHARS.sub("_", s).strip(" .")[:limit] or default


def decode_text(data: bytes) -> str:
    """字节 -> 文本：依次尝试 utf-8(含 BOM)、gb18030，都失败则宽容解码。"""
    for enc in ("utf-8-sig", "gb18030"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")
