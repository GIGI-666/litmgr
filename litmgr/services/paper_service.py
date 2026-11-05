"""论文服务。

【作用】论文的增删改查中心：创建论文、修改字段值、阅读状态/星级、管理论文文件。
【职责】
    - 写入字段值时按字段类型规范化（core.field_types），并同步更新全文索引
    - 每次字段修改写入修改历史（用于查看与撤销）
    - 修改后发布事件，界面自动刷新
    - 管理论文文件（复制进文献库、记录、索引翻译正文、删除）
    - 计算论文显示标题（按“角色”取字段，不依赖字段名）
【依赖】storage 各仓库、storage.library_fs、services.field_service、core.events。
【被谁调用】ui 各窗口、services.import_service / compare_service / history_service。
【扩展点】新的“论文级属性”（如优先级）在这里加方法，并发布 PAPER_CHANGED。
"""

from __future__ import annotations

from pathlib import Path

from ..core.errors import NotFoundError, ValidationError
from ..core.events import EventBus, Events
from ..core.field_types import get_type
from ..core.models import (KIND_TRANSLATION, READ_STATUS, ROLE_ARXIV, ROLE_TITLE,
                           ROLE_TITLE_EN, FieldValue, Paper, PaperFile)
from ..storage.file_repo import FileRepo
from ..storage.library_fs import LibraryFS
from ..storage.log_repo import LogRepo
from ..storage.note_repo import NoteRepo
from ..storage.paper_repo import PaperRepo
from ..storage.search_repo import SearchRepo
from .field_service import FieldService


class PaperService:
    def __init__(self, paper_repo: PaperRepo, file_repo: FileRepo, search_repo: SearchRepo,
                 log_repo: LogRepo, note_repo: NoteRepo, fields: FieldService,
                 fs: LibraryFS, events: EventBus) -> None:
        self.papers = paper_repo
        self.files = file_repo
        self.search = search_repo
        self.log = log_repo
        self.notes = note_repo
        self.fields = fields
        self.fs = fs
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

    def exists(self, paper_id: int) -> bool:
        return self.papers.exists(paper_id)

    def count(self) -> int:
        return len(self.papers.all_ids())

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
        for f in self.files.list_for_paper(paper_id):
            self.search.remove_file(f.id)
        for v in self.papers.load_papers([paper_id]):
            for fid in v.values:
                self.search.remove_field(paper_id, fid)
        self.search.index_notes(paper_id, "")
        self.papers.delete(paper_id)
        self.fs.remove_paper_dir(paper_id)
        self.events.publish(Events.PAPER_DELETED, paper_id=paper_id)

    def set_archived(self, paper_id: int, archived: bool) -> None:
        self.papers.set_archived(paper_id, archived)
        self.events.publish(Events.PAPER_CHANGED, paper_id=paper_id)

    # ---------- 字段值 ----------
    def _write_value(self, paper_id: int, field_id: int, raw: str) -> FieldValue:
        f = self.fields.get(field_id)
        text, js = get_type(f.type).parse(raw, f.options)
        val = FieldValue(text, js)
        if text:
            self.papers.set_value(paper_id, field_id, val)
        else:
            self.papers.delete_value(paper_id, field_id)
        self.search.index_field(paper_id, field_id, text)
        return val

    def set_field(self, paper_id: int, field_id: int, raw: str, *, log: bool = True) -> FieldValue:
        """修改某论文的某字段。值未变化时不做任何事。返回规范化后的值。"""
        if not self.papers.exists(paper_id):
            raise NotFoundError(f"论文不存在: {paper_id}")
        f = self.fields.get(field_id)
        old = self.papers.get_value(paper_id, field_id)
        new_text, _ = get_type(f.type).parse(raw, f.options)
        if new_text == old.text:
            return old
        with self.papers.db.transaction():
            val = self._write_value(paper_id, field_id, raw)
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

    # ---------- 文件 ----------
    def list_files(self, paper_id: int, kind: str | None = None) -> list[PaperFile]:
        return self.files.list_for_paper(paper_id, kind)

    def add_file(self, paper_id: int, kind: str, src: Path | str, *, subtype: str = "",
                 display_name: str | None = None, publish: bool = True) -> PaperFile:
        """把外部文件复制进文献库并登记。翻译文件会同时建立正文索引。"""
        src = Path(src)
        rel, digest = self.fs.add_file(paper_id, kind, src)
        fid = self.files.add(paper_id, kind, rel, display_name or src.name, subtype, digest)
        if kind == KIND_TRANSLATION:
            self._index_translation(paper_id, fid, rel)
        if publish:
            self.events.publish(Events.FILES_CHANGED, paper_id=paper_id)
        return self.files.get(fid)

    def _index_translation(self, paper_id: int, file_id: int, rel_path: str) -> None:
        try:
            self.search.index_file(paper_id, file_id, self.fs.read_text(rel_path))
        except OSError:
            pass  # 文件读不到时不影响其他功能

    def reindex_file(self, file_id: int) -> None:
        f = self.files.get(file_id)
        if f and f.kind == KIND_TRANSLATION:
            self._index_translation(f.paper_id, f.id, f.rel_path)

    def remove_file(self, file_id: int) -> None:
        f = self.files.get(file_id)
        if not f:
            return
        self.search.remove_file(file_id)
        self.files.delete(file_id)
        # 同一物理文件可能被别的记录复用（理论上不会，但保险起见）
        if not any(x.rel_path == f.rel_path for x in self.files.find_by_hash(f.sha256)):
            self.fs.remove_file(f.rel_path)
        self.events.publish(Events.FILES_CHANGED, paper_id=f.paper_id)

    def set_file_subtype(self, file_id: int, subtype: str) -> None:
        f = self.files.get(file_id)
        if f:
            self.files.update_subtype(file_id, subtype)
            self.events.publish(Events.FILES_CHANGED, paper_id=f.paper_id)

    def abs_path(self, f: PaperFile) -> Path:
        return self.fs.abs_path(f.rel_path)

    def read_text(self, f: PaperFile) -> str:
        return self.fs.read_text(f.rel_path)

    # ---------- 全库重建索引 ----------
    def reindex_all(self) -> None:
        """重建全文索引（恢复备份、手动修复时用）。"""
        self.search.clear()
        for p in self.papers.load_papers():
            for fid, val in p.values.items():
                self.search.index_field(p.id, fid, val.text)
            self.search.index_notes(p.id, self.notes.all_text(p.id))
            for f in self.files.list_for_paper(p.id, KIND_TRANSLATION):
                self._index_translation(p.id, f.id, f.rel_path)
