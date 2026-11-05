"""论文服务。

【作用】论文的增删改查中心：创建论文、修改字段值、阅读状态/星级。
    论文文件的管理由 services.file_service 负责，待归类内容由 services.pending_service 负责。
【职责】
    - 写入字段值时按字段类型规范化（core.field_types），并同步更新全文索引
    - 每次字段修改写入修改历史（用于查看与撤销）
    - 修改后发布事件，界面自动刷新
    - 计算论文显示标题（按“角色”取字段，不依赖字段名）
【依赖】storage 各仓库、services.field_service / file_service、core.events。
【被谁调用】ui 各窗口、services.import_service / compare_service / history_service。
【扩展点】新的“论文级属性”（如优先级）在这里加方法，并发布 PAPER_CHANGED。
"""

from __future__ import annotations

from ..core.errors import NotFoundError, ValidationError
from ..core.events import EventBus, Events
from ..core.field_types import get_type
from ..core.models import (READ_STATUS, ROLE_ARXIV, ROLE_TITLE, ROLE_TITLE_EN, FieldValue,
                           Paper)
from ..storage.log_repo import LogRepo
from ..storage.note_repo import NoteRepo
from ..storage.paper_repo import PaperRepo
from ..storage.search_repo import SearchRepo
from .field_service import FieldService
from .file_service import FileService


class PaperService:
    def __init__(self, paper_repo: PaperRepo, search_repo: SearchRepo, log_repo: LogRepo,
                 note_repo: NoteRepo, fields: FieldService, files: FileService,
                 events: EventBus) -> None:
        self.papers = paper_repo
        self.files = files
        self.search = search_repo
        self.log = log_repo
        self.notes = note_repo
        self.fields = fields
        self.events = events

    # ---------- 读取 ----------
    def _fill_titles(self, papers: list[Paper]) -> list[Paper]:
        ids = [self.fields.by_role(r) for r in (ROLE_TITLE, ROLE_TITLE_EN, ROLE_ARXIV)]
        for p in papers:
            title = ""
            for f in ids:
                if f and (t := p.text_of(f.id).strip()):
                    title = t.splitlines()[0]
                    break
            p.title = title or f"（未命名论文 #{p.id}）"
        return papers

    def get(self, paper_id: int) -> Paper:
        found = self.papers.load_papers([paper_id])
        if not found:
            raise NotFoundError(f"论文不存在: {paper_id}")
        return self._fill_titles(found)[0]

    def get_many(self, paper_ids: list[int]) -> list[Paper]:
        return self._fill_titles(self.papers.load_papers(paper_ids))

    def list_all(self, include_archived: bool = False) -> list[Paper]:
        papers = self._fill_titles(self.papers.load_papers())
        return papers if include_archived else [p for p in papers if not p.archived]

    def list_titles(self, include_archived: bool = False) -> list[Paper]:
        """轻量列表：只读取标题相关字段（选择论文的对话框等只需要标题的场合用）。"""
        fids = [f.id for r in (ROLE_TITLE, ROLE_TITLE_EN, ROLE_ARXIV)
                if (f := self.fields.by_role(r))]
        papers = self._fill_titles(self.papers.load_papers(field_ids=fids))
        return papers if include_archived else [p for p in papers if not p.archived]

    def exists(self, paper_id: int) -> bool:
        return self.papers.exists(paper_id)

    def get_field_text(self, paper_id: int, field_id: int) -> str:
        """读取某论文某字段当前的文本（没有则为空串）。"""
        return self.papers.get_value(paper_id, field_id).text

    def transaction(self):
        """事务上下文：with 块内的多步修改要么全部成功，要么全部撤销（可嵌套）。"""
        return self.papers.db.transaction()

    def count(self) -> int:
        return self.papers.count()

    # ---------- 创建 / 删除 ----------
    def create(self, raw_values: dict[int, str] | None = None, *, publish: bool = True) -> int:
        """创建论文，可同时写入初始字段值（{字段id: 原始文本}）。创建不记入修改历史。"""
        with self.papers.db.transaction():
            pid = self.papers.create()
            for fid, raw in (raw_values or {}).items():
                self._write_value(pid, fid, raw)
        if publish:
            self.events.publish(Events.PAPER_ADDED, paper_id=pid)
        return pid

    def delete(self, paper_id: int) -> None:
        """永久删除论文及其库内文件、索引。"""
        with self.papers.db.transaction():     # 数据库部分要么全删，要么全不删
            self.files.drop_index_of_paper(paper_id)
            for v in self.papers.load_papers([paper_id]):
                for fid in v.values:
                    self.search.remove_field(paper_id, fid)
            self.search.index_notes(paper_id, "")
            self.papers.delete(paper_id)
        self.files.discard_dir(paper_id)       # 数据库提交成功后再删文件
        self.events.publish(Events.PAPER_DELETED, paper_id=paper_id)

    def set_archived(self, paper_id: int, archived: bool) -> None:
        self.papers.set_archived(paper_id, archived)
        self.events.publish(Events.PAPER_CHANGED, paper_id=paper_id)

    # ---------- 字段值 ----------
    def _parse(self, field_id: int, raw: str) -> FieldValue:
        """按字段类型把原始输入规范化为字段值。"""
        f = self.fields.get(field_id)
        text, js = get_type(f.type).parse(raw, f.options)
        return FieldValue(text, js)

    def _store_value(self, paper_id: int, field_id: int, val: FieldValue) -> None:
        """写入（或清空）字段值，并同步全文索引。"""
        if val.text:
            self.papers.set_value(paper_id, field_id, val)
        else:
            self.papers.delete_value(paper_id, field_id)
        self.search.index_field(paper_id, field_id, val.text)

    def _write_value(self, paper_id: int, field_id: int, raw: str) -> FieldValue:
        val = self._parse(field_id, raw)
        self._store_value(paper_id, field_id, val)
        return val

    def set_field(self, paper_id: int, field_id: int, raw: str, *, log: bool = True) -> FieldValue:
        """修改某论文的某字段。值未变化时不做任何事。返回规范化后的值。"""
        if not self.papers.exists(paper_id):
            raise NotFoundError(f"论文不存在: {paper_id}")
        f = self.fields.get(field_id)
        old = self.papers.get_value(paper_id, field_id)
        val = self._parse(field_id, raw)          # 只解析一次
        if val.text == old.text:
            return old
        with self.papers.db.transaction():
            self._store_value(paper_id, field_id, val)
            self.papers.touch(paper_id)
            if log:
                self.log.add_change(paper_id, field_id, f.name, old.text, val.text)
        self.events.publish(Events.PAPER_CHANGED, paper_id=paper_id)
        return val

    def set_status(self, paper_id: int, status: str) -> None:
        if status not in READ_STATUS:
            raise ValidationError(f"未知阅读状态: {status}")
        self.papers.set_status(paper_id, status)
        self.events.publish(Events.PAPER_CHANGED, paper_id=paper_id)

    def set_rating(self, paper_id: int, rating: int) -> None:
        self.papers.set_rating(paper_id, max(0, min(5, int(rating))))
        self.events.publish(Events.PAPER_CHANGED, paper_id=paper_id)

    # ---------- 全库重建索引 ----------
    def reindex_all(self) -> None:
        """重建全文索引（恢复备份、手动修复时用）。"""
        with self.papers.db.transaction():     # 整体一个事务：几千篇时从几十秒降到几秒
            self.search.clear()
            for p in self.papers.load_papers():
                for fid, val in p.values.items():
                    self.search.index_field(p.id, fid, val.text)
                self.search.index_notes(p.id, self.notes.all_text(p.id))
                self.files.reindex_translations(p.id)
