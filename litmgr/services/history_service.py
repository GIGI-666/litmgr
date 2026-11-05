"""修改历史与撤销服务。

【作用】查看字段值的修改历史，并可撤销误操作（把字段恢复为修改前的值）。
【说明】历史由 paper_service.set_field 自动记录；撤销本身不再产生新的历史记录，
    只把原记录标记为“已撤销”，避免撤销链混乱。
【依赖】storage.log_repo；services.paper_service。
【被谁调用】ui.history_panel / 主窗口“编辑 -> 撤销”。
"""

from __future__ import annotations

from ..core.errors import NotFoundError, ValidationError
from ..core.models import ChangeLogEntry
from ..storage.log_repo import LogRepo
from .paper_service import PaperService


class HistoryService:
    def __init__(self, log_repo: LogRepo, papers: PaperService) -> None:
        self.log = log_repo
        self.papers = papers

    def of_paper(self, paper_id: int) -> list[ChangeLogEntry]:
        return self.log.history_of_paper(paper_id)

    def recent(self, limit: int = 100) -> list[ChangeLogEntry]:
        return self.log.recent(limit)

    def undo(self, entry_id: int) -> ChangeLogEntry:
        """撤销指定的一条修改（恢复旧值）。"""
        e = self.log.get_change(entry_id)
        if e is None:
            raise NotFoundError("历史记录不存在")
        if e.undone:
            raise ValidationError("这条修改已经撤销过了")
        if e.field_id is None:
            raise ValidationError("这条记录不支持撤销")
        self.papers.set_field(e.paper_id, e.field_id, e.old_value, log=False)
        self.log.mark_undone(e.id)
        return e

    def undo_last(self) -> ChangeLogEntry | None:
        e = self.log.last_undoable()
        return self.undo(e.id) if e else None
