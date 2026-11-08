"""字段管理服务。

【作用】管理“论文卡片有哪些字段”：新增、改名、改类型、调整顺序/分组、别名、归档与恢复。
    所有论文共用同一套字段；字段可随时增删改而不丢数据。
【职责】
    - 字段名查重（同时避免与别名冲突）
    - 改字段类型时，用新类型重新解析所有论文的该字段值（value_text 永不丢失）
    - 字段“归档”（软删除，可恢复）与“永久删除”
    - 字段分组新建、改名、删除；删除分组保留其字段及论文内容
    - 提供“名称/别名 -> 字段”的查找表，供卡片导入识别字段
    - 首次创建文献库时写入默认的 25 个模板字段
【依赖】storage.field_repo / paper_repo / search_repo；core.field_types / events。
【被谁调用】ui.field_manager_dialog、services.import_service、services.paper_service。
【扩展点】新的内置默认字段在 DEFAULT_FIELDS 增加一行即可。
"""

from __future__ import annotations

from ..core.errors import DuplicateError, NotFoundError, ValidationError
from ..core.events import EventBus, Events
from ..core.field_types import FIELD_TYPES, get_type
from ..core.models import (ROLE_ARXIV, ROLE_DATE_FIRST, ROLE_DATE_PUB, ROLE_TITLE,
                           ROLE_TITLE_EN, ROLE_VENUE, FieldDef)
from ..core.textutil import normalize_label
from ..storage.field_repo import FieldRepo
from ..storage.paper_repo import PaperRepo
from ..storage.search_repo import SearchRepo

# (名称, 类型, 角色, 别名, 分组, 是否在列表显示, 候选项)
DEFAULT_FIELDS: list[tuple] = [
    ("一句话总结论文主要内容", "longtext", None, ["一句话总结"], "概要", False, []),
    ("英文标题", "text", ROLE_TITLE_EN, [], "概要", True, []),
    ("中文标题", "text", ROLE_TITLE, [], "概要", True, []),
    ("论文类型", "select", None, [], "基本信息", True,
     ["方法型研究论文", "综述", "基准/数据集论文"]),
    ("研究领域", "tags", None, ["论文研究方向"], "基本信息", False, []),
    ("论文所属会议/期刊", "text", ROLE_VENUE, ["会议/期刊", "论文所属会议期刊"], "基本信息", True, []),
    ("arXiv编号", "text", ROLE_ARXIV, [], "基本信息", False, []),
    ("arXiv分类", "text", None, [], "基本信息", False, []),
    ("论文首次公开日期", "date", ROLE_DATE_FIRST,
     ["论文首次发布日期", "首次发布日期", "首次公开日期"], "基本信息", True, []),
    ("论文正式发表日期", "date", ROLE_DATE_PUB, ["正式发表日期"], "基本信息", False, []),
    ("页数", "text", None, [], "基本信息", False, []),
    ("正式代码地址", "url", None, ["代码地址"], "基本信息", False, []),
    ("作者名称", "longtext", None, ["作者"], "基本信息", False, []),
    ("作者所属机构", "longtext", None, ["作者机构", "作者单位"], "基本信息", False, []),
    ("研究问题", "longtext", None, [], "内容", False, []),
    ("此论文以前的方法的问题", "longtext", None, [], "内容", False, []),
    ("核心思想/关键创新", "longtext", None, [], "内容", False, []),
    ("方法流程图/论文主图流程图", "longtext", None, ["方法流程图/论文主图的流程图"], "内容", False, []),
    ("训练数据", "longtext", None, [], "实验", False, []),
    ("测试数据", "longtext", None, [], "实验", False, []),
    ("指标", "longtext", None, [], "实验", False, []),
    ("主要结果", "longtext", None, [], "实验", False, []),
    ("实验/消融实验", "longtext", None, ["消融实验"], "实验", False, []),
    ("局限性", "longtext", None, [], "我的思考", False, []),
    ("与我研究方向的关系和启发", "longtext", None, [], "我的思考", False, []),
]

class FieldService:
    def __init__(self, repo: FieldRepo, paper_repo: PaperRepo, search_repo: SearchRepo,
                 events: EventBus) -> None:
        self.repo = repo
        self.paper_repo = paper_repo
        self.search_repo = search_repo
        self.events = events

    # ---------- 查询 ----------
    def list(self, include_archived: bool = False) -> list[FieldDef]:
        return self.repo.list(include_archived)

    def get(self, field_id: int) -> FieldDef:
        f = self.repo.get(field_id)
        if f is None:
            raise NotFoundError(f"字段不存在: {field_id}")
        return f

    def by_role(self, role: str) -> FieldDef | None:
        for f in self.repo.list(include_archived=False):
            if f.role == role:
                return f
        return None

    def name_lookup(self) -> dict[str, int]:
        """归一化后的 名称/别名 -> 字段 id。导入识别字段用。"""
        out: dict[str, int] = {}
        for f in self.repo.list(include_archived=False):
            for n in [f.name, *f.aliases]:
                out.setdefault(normalize_label(n), f.id)
        return out

    def groups(self) -> list[str]:
        """列出所有已保存的分组，空分组也保留。"""
        return self.repo.groups()

    # ---------- 字段分组（与论文标签/分组无关） ----------
    def _check_group_name(self, name: str, exclude: str | None = None) -> str:
        name = (name or "").strip()
        if not name:
            raise ValidationError("分组名不能为空")
        key = normalize_label(name)
        if key == normalize_label("未分组"):
            raise ValidationError("未分组是系统保留名称，请使用其他分组名")
        if any(g != exclude and normalize_label(g) == key for g in self.groups()):
            raise DuplicateError(f"已存在同名字段分组：{name}")
        return name

    def _require_group(self, name: str) -> None:
        if name not in self.groups():
            raise NotFoundError(f"字段分组不存在：{name}")

    def _group_for_field(self, name: str) -> str:
        """字段编辑允许直接输入新组名，同名写法统一到已有分组。"""
        name = (name or "").strip()
        if not name:
            return ""
        for group in self.groups():
            if normalize_label(group) == normalize_label(name):
                return group
        return self._check_group_name(name)

    def add_group(self, name: str) -> str:
        """新建可独立保存的空分组，返回去除首尾空白后的名称。"""
        name = self._check_group_name(name)
        self.repo.ensure_group(name)
        self.events.publish(Events.FIELDS_CHANGED)
        return name

    def rename_group(self, old_name: str, new_name: str) -> str:
        """原子改组名并同步组内所有字段，不改变字段编号和论文内容。"""
        self._require_group(old_name)
        new_name = self._check_group_name(new_name, exclude=old_name)
        if new_name != old_name:
            with self.repo.db.transaction():
                self.repo.rename_group(old_name, new_name)
            self.events.publish(Events.FIELDS_CHANGED)
        return new_name

    def delete_group(self, name: str) -> None:
        """删除分组，组内字段（含已归档字段）全部移到未分组。"""
        self._require_group(name)
        with self.repo.db.transaction():
            self.repo.delete_group(name)
        self.events.publish(Events.FIELDS_CHANGED)

    # ---------- 校验 ----------
    def _check_name(self, name: str, exclude_id: int | None = None) -> str:
        name = (name or "").strip()
        if not name:
            raise ValidationError("字段名不能为空")
        key = normalize_label(name)
        for f in self.repo.list(include_archived=True):
            if f.id == exclude_id:
                continue
            if key == normalize_label(f.name):
                raise DuplicateError(f"已存在同名字段：{f.name}" + ("（已归档）" if f.archived else ""))
        return name

    @staticmethod
    def _check_type(type_name: str) -> None:
        if type_name not in FIELD_TYPES:
            raise ValidationError(f"未知字段类型: {type_name}")

    # ---------- 增改 ----------
    def add(self, name: str, type: str = "longtext", *, options: list[str] | None = None,
            aliases: list[str] | None = None, role: str | None = None, group_name: str = "",
            show_in_list: bool = False, publish: bool = True) -> FieldDef:
        name = self._check_name(name)
        self._check_type(type)
        group_name = self._group_for_field(group_name)
        f = FieldDef(id=0, name=name, type=type, options=list(options or []),
                     aliases=list(aliases or []), role=role, group_name=group_name,
                     sort_order=self.repo.max_sort_order() + 1, show_in_list=show_in_list)
        with self.repo.db.transaction():
            self.repo.ensure_group(group_name)
            f.id = self.repo.insert(f)
        if publish:
            self.events.publish(Events.FIELDS_CHANGED)
        return f

    def update(self, f: FieldDef) -> FieldDef:
        """保存对字段定义的修改（改名、候选项、别名、分组、列表显示、类型）。"""
        old = self.get(f.id)
        f.name = self._check_name(f.name, exclude_id=f.id)
        self._check_type(f.type)
        f.group_name = self._group_for_field(f.group_name)
        with self.repo.db.transaction():       # 字段定义与所有论文的值要么一起改，要么都不改
            self.repo.ensure_group(f.group_name)
            self.repo.update(f)
            if old.type != f.type:
                self._reparse_values(f)
        self.events.publish(Events.FIELDS_CHANGED)
        return f

    def set_show_in_list(self, field_id: int, on: bool) -> None:
        """切换某字段是否作为论文列表的一列显示。

        只发布 LIST_COLUMNS_CHANGED（只有列表需要刷新），不发布 FIELDS_CHANGED，
        以免已打开的详情/对比窗口白白重建表单、丢掉未保存的输入。
        """
        f = self.get(field_id)
        if f.show_in_list == on:
            return
        f.show_in_list = on
        self.repo.update(f)
        self.events.publish(Events.LIST_COLUMNS_CHANGED)

    def _reparse_values(self, f: FieldDef) -> None:
        """字段类型变化后，用新类型重新解析所有论文的该字段值。value_text 保证不丢。"""
        ftype = get_type(f.type)
        for paper_id, val in self.paper_repo.values_of_field(f.id):
            text, js = ftype.parse(val.text, f.options)
            val.text, val.json = text, js
            self.paper_repo.set_value(paper_id, f.id, val)
            self.search_repo.index_field(paper_id, f.id, text)

    def preview_type_change(self, field_id: int, new_type: str) -> tuple[int, int]:
        """改类型前的预览：返回 (会被规范化改写的值数量, 无法按新类型解析而保留原文的数量)。"""
        f = self.get(field_id)
        ftype = get_type(new_type)
        changed = unparsed = 0
        for _pid, val in self.paper_repo.values_of_field(field_id):
            text, js = ftype.parse(val.text, f.options)
            if text != val.text:
                changed += 1
            if js is None and val.text.strip() and new_type in ("number", "date", "rating"):
                unparsed += 1
        return changed, unparsed

    def add_alias(self, field_id: int, alias: str) -> None:
        """给字段增加别名（导入向导“映射到已有字段”时调用，使以后能自动识别）。"""
        f = self.get(field_id)
        key = normalize_label(alias)
        if key and key != normalize_label(f.name) and \
                key not in [normalize_label(a) for a in f.aliases]:
            f.aliases.append(alias.strip())
            self.repo.update(f)
            self.events.publish(Events.FIELDS_CHANGED)

    def reorder(self, ordered_ids: list[int]) -> None:
        """按给定顺序重排字段。"""
        with self.repo.db.transaction():
            for i, fid in enumerate(ordered_ids):
                f = self.repo.get(fid)
                if f and f.sort_order != i:
                    f.sort_order = i
                    self.repo.update(f)
        self.events.publish(Events.FIELDS_CHANGED)

    # ---------- 归档 / 删除 ----------
    def archive(self, field_id: int) -> None:
        f = self.get(field_id)
        f.archived = True
        self.repo.update(f)
        self.events.publish(Events.FIELDS_CHANGED)

    def restore(self, field_id: int) -> None:
        f = self.get(field_id)
        f.archived = False
        self.repo.update(f)
        self.events.publish(Events.FIELDS_CHANGED)

    def delete_permanently(self, field_id: int) -> None:
        """永久删除字段及所有论文中的该字段数据。只允许删除已归档的字段。"""
        f = self.get(field_id)
        if not f.archived:
            raise ValidationError("请先归档字段，再永久删除")
        pids = [pid for pid, _ in self.paper_repo.values_of_field(field_id)]
        with self.repo.db.transaction():
            self.search_repo.remove_field_everywhere(field_id, pids)
            self.repo.delete(field_id)
        self.events.publish(Events.FIELDS_CHANGED)

    # ---------- 默认字段 ----------
    def seed_defaults_if_empty(self) -> None:
        """全新文献库时写入模板里的 25 个字段。"""
        if self.repo.list(include_archived=True):
            return
        with self.repo.db.transaction():
            for name, typ, role, aliases, group, show, options in DEFAULT_FIELDS:
                self.add(name, typ, options=options, aliases=aliases, role=role,
                         group_name=group, show_in_list=show, publish=False)
        self.events.publish(Events.FIELDS_CHANGED)
