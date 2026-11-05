"""论文文件服务。

【作用】管理论文附带的文件（卡片 txt / PDF / 翻译 md / 附件）：复制进文献库、登记、
    设置子类型、移除、读取内容。翻译文件会同时建立全文索引，使其能被搜索。
    从 PaperService 中拆出：论文字段管理与文件管理是两件事，互不依赖对方。
【依赖】storage.file_repo / search_repo / library_fs；core.events。
【被谁调用】ui.file_panel / reader_window / main_window；services.import_service、paper_service
    （删除论文、重建索引时需要文件列表与翻译索引）。
"""

from __future__ import annotations

from pathlib import Path

from ..core.events import EventBus, Events
from ..core.models import KIND_TRANSLATION, PaperFile
from ..storage.file_repo import FileRepo
from ..storage.library_fs import LibraryFS
from ..storage.search_repo import SearchRepo


class FileService:
    def __init__(self, file_repo: FileRepo, search_repo: SearchRepo, fs: LibraryFS,
                 events: EventBus) -> None:
        self.files = file_repo
        self.search = search_repo
        self.fs = fs
        self.events = events

    # ---------- 读取 ----------
    def list(self, paper_id: int, kind: str | None = None) -> list[PaperFile]:
        return self.files.list_for_paper(paper_id, kind)

    def abs_path(self, f: PaperFile) -> Path:
        return self.fs.abs_path(f.rel_path)

    def read_text(self, f: PaperFile) -> str:
        return self.fs.read_text(f.rel_path)

    # ---------- 修改 ----------
    def add(self, paper_id: int, kind: str, src: Path | str, *, subtype: str = "",
            display_name: str | None = None, publish: bool = True) -> PaperFile:
        """把外部文件复制进文献库并登记。翻译文件会同时建立正文索引。"""
        src = Path(src)
        rel, digest = self.fs.add_file(paper_id, kind, src)
        fid = self.files.add(paper_id, kind, rel, display_name or src.name, subtype, digest)
        if kind == KIND_TRANSLATION:
            self.index_translation(paper_id, fid, rel)
        if publish:
            self.events.publish(Events.FILES_CHANGED, paper_id=paper_id)
        return self.files.get(fid)

    def remove(self, file_id: int) -> None:
        f = self.files.get(file_id)
        if not f:
            return
        self.search.remove_file(file_id)
        self.files.delete(file_id)
        # 同一物理文件可能被别的记录复用（理论上不会，但保险起见）
        if not any(x.rel_path == f.rel_path for x in self.files.find_by_hash(f.sha256)):
            self.fs.remove_file(f.rel_path)
        self.events.publish(Events.FILES_CHANGED, paper_id=f.paper_id)

    def set_subtype(self, file_id: int, subtype: str) -> None:
        f = self.files.get(file_id)
        if f:
            self.files.update_subtype(file_id, subtype)
            self.events.publish(Events.FILES_CHANGED, paper_id=f.paper_id)

    # ---------- 索引 ----------
    def index_translation(self, paper_id: int, file_id: int, rel_path: str) -> None:
        try:
            self.search.index_file(paper_id, file_id, self.fs.read_text(rel_path))
        except OSError:
            pass  # 文件读不到时不影响其他功能

    def drop_index_of_paper(self, paper_id: int) -> None:
        """删除论文前，清掉它所有文件的索引。"""
        for f in self.files.list_for_paper(paper_id):
            self.search.remove_file(f.id)

    def reindex_translations(self, paper_id: int) -> None:
        for f in self.files.list_for_paper(paper_id, KIND_TRANSLATION):
            self.index_translation(paper_id, f.id, f.rel_path)

    def discard_dir(self, paper_id: int) -> None:
        """删除某论文在文献库里的文件夹（删除论文、导入失败回滚后清理已复制文件用）。"""
        self.fs.remove_paper_dir(paper_id)
