"""应用上下文：全系统唯一的“装配点”。

【作用】创建并连接所有仓库与服务，界面只需要持有一个 AppContext 就能访问全部业务能力。
    依赖关系在这里集中体现，其他模块互相不创建对方，因此可以单独替换/测试任何一个服务。
【用法】
    ctx = AppContext(Path("D:/文献库"))
    ctx.papers.list_all(); ctx.search.run(...); ctx.close()
【扩展点】新增服务：在 __init__ 里创建并赋给属性即可；插件可通过 ctx 取用所有服务。
【依赖】storage / services 下全部模块。
"""

from __future__ import annotations

from pathlib import Path

from ..core.events import EventBus
from ..storage.database import Database
from ..storage.field_repo import FieldRepo
from ..storage.file_repo import FileRepo
from ..storage.library_fs import LibraryFS
from ..storage.log_repo import LogRepo
from ..storage.note_repo import NoteRepo
from ..storage.organize_repo import OrganizeRepo
from ..storage.paper_repo import PaperRepo
from ..storage.pending_repo import PendingRepo
from ..storage.reading_repo import ReadingRepo
from ..storage.search_repo import SearchRepo
from .backup_service import BackupService
from .compare_service import CompareService
from .export_service import ExportService
from .field_service import FieldService
from .file_service import FileService
from .history_service import HistoryService
from .import_service import ImportService
from .note_service import NoteService
from .organize_service import OrganizeService
from .paper_service import PaperService
from .pending_service import PendingService
from .reading_history_service import ReadingHistoryService
from .search_service import SearchService


class AppContext:
    def __init__(self, library_path: Path | str) -> None:
        self.events = EventBus()
        self.fs = LibraryFS(library_path)
        self.db = Database(self.fs.db_path, backup_dir=self.fs.backups_dir)

        # 仓库（storage）
        field_repo = FieldRepo(self.db)
        paper_repo = PaperRepo(self.db)
        file_repo = FileRepo(self.db)
        search_repo = SearchRepo(self.db)
        log_repo = LogRepo(self.db)
        note_repo = NoteRepo(self.db)
        organize_repo = OrganizeRepo(self.db)

        # 服务（services）
        self.fields = FieldService(field_repo, paper_repo, search_repo, self.events)
        self.fields.seed_defaults_if_empty()
        self.files = FileService(file_repo, search_repo, self.fs, self.events)
        self.papers = PaperService(paper_repo, search_repo, log_repo, note_repo,
                                   self.fields, self.files, self.events)
        self.search = SearchService(search_repo, organize_repo, self.fields, self.papers)
        self.organize = OrganizeService(organize_repo, self.events)
        self.notes = NoteService(note_repo, search_repo, self.events)
        self.history = HistoryService(log_repo, self.papers)
        self.reading = ReadingHistoryService(ReadingRepo(self.db), self.papers, self.events)
        self.pending = PendingService(PendingRepo(self.db), self.papers, self.events)
        self.imports = ImportService(self.fields, self.papers, self.files, self.pending,
                                     self.organize, self.events)
        self.compare = CompareService(self.papers, self.fields)
        self.export = ExportService(self.papers, self.fields)
        self.backup = BackupService(self.db, self.fs, self.papers, self.events)

    @property
    def library_path(self) -> Path:
        return self.fs.root

    def close(self) -> None:
        self.db.close()
