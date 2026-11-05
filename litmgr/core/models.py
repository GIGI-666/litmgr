"""领域数据模型。

【作用】定义系统里流转的“数据对象”：字段定义、论文、论文文件、标签、分组、笔记等。
    这些是纯数据类（dataclass），不含数据库或界面代码，所以各层都可安全引用。
【依赖】仅标准库。
【被谁调用】storage 仓库构造它们；services 加工它们；ui 展示它们。
【扩展点】新增实体时在此加 dataclass，再到 storage 加对应仓库。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# 论文文件种类
KIND_CARD = "card"
KIND_PDF = "pdf"
KIND_TRANSLATION = "translation"
KIND_ATTACHMENT = "attachment"
KIND_LABELS = {KIND_CARD: "论文卡片", KIND_PDF: "PDF", KIND_TRANSLATION: "翻译",
               KIND_ATTACHMENT: "附件"}

# PDF 子类型
SUBTYPE_MAIN = "正文"
SUBTYPE_SUPPLEMENT = "补充材料"
SUBTYPE_APPENDIX = "附录"

# 阅读状态
READ_STATUS = {"unread": "未读", "reading": "在读", "read": "已读", "deep": "精读"}

# 字段的“角色”：系统功能（配对、查重、标题显示）靠角色而不是靠字段名，所以改名不受影响
ROLE_TITLE = "title"
ROLE_TITLE_EN = "title_en"
ROLE_ARXIV = "arxiv_id"
ROLE_DATE_FIRST = "date_first"
ROLE_DATE_PUB = "date_pub"
ROLE_VENUE = "venue"


@dataclass
class FieldDef:
    """字段定义。id 稳定不变；name 可随意修改。"""

    id: int
    name: str
    type: str = "longtext"
    options: list[str] = field(default_factory=list)   # 单选候选项
    aliases: list[str] = field(default_factory=list)   # 导入识别用的别名
    role: str | None = None
    group_name: str = ""
    sort_order: int = 0
    show_in_list: bool = False
    archived: bool = False


@dataclass
class FieldValue:
    """一个字段的值：文本形态 + 结构化形态。"""

    text: str = ""
    json: Any = None

    @property
    def empty(self) -> bool:
        return not self.text.strip()


@dataclass
class Paper:
    """一篇论文。values 以 field_id 为键。"""

    id: int
    created_at: str = ""
    updated_at: str = ""
    read_status: str = "unread"
    rating: int = 0
    archived: bool = False
    values: dict[int, FieldValue] = field(default_factory=dict)
    title: str = ""  # 由 paper_service 按角色计算出的显示标题

    def text_of(self, field_id: int) -> str:
        v = self.values.get(field_id)
        return v.text if v else ""


@dataclass
class PaperFile:
    """论文关联的一个文件（卡片/PDF/翻译/附件）。rel_path 相对于文献库根目录。"""

    id: int
    paper_id: int
    kind: str
    subtype: str = ""
    rel_path: str = ""
    display_name: str = ""
    sha256: str = ""
    added_at: str = ""


@dataclass
class Tag:
    id: int
    name: str
    color: str = ""


@dataclass
class Collection:
    id: int
    name: str
    sort_order: int = 0


@dataclass
class SavedView:
    id: int
    name: str
    query: dict = field(default_factory=dict)


@dataclass
class Note:
    id: int
    paper_id: int
    content: str
    created_at: str = ""
    updated_at: str = ""


@dataclass
class ChangeLogEntry:
    """字段修改历史，用于查看与撤销。"""

    id: int
    paper_id: int
    field_id: int | None
    field_name: str
    old_value: str
    new_value: str
    changed_at: str
    undone: bool = False


@dataclass
class PendingContent:
    """导入时未能归入任何字段的内容，等待用户归类。"""

    id: int
    paper_id: int
    label: str
    content: str
