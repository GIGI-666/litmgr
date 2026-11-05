"""待归类内容服务。

【作用】管理导入时“没地方放”的内容：列出、并入某个字段、丢弃。
    原先混在导入服务里，导入只负责“产生”待归类内容，之后的处理独立到这里。
【依赖】storage.pending_repo；services.paper_service；core.events。
【被谁调用】services.import_service（暂存）；ui.field_form（并入/丢弃）、ui.import_wizard（统计）。
"""

from __future__ import annotations

from ..core.events import EventBus, Events
from ..core.models import PendingContent
from ..storage.pending_repo import PendingRepo
from .paper_service import PaperService


class PendingService:
    def __init__(self, repo: PendingRepo, papers: PaperService, events: EventBus) -> None:
        self.repo = repo
        self.papers = papers
        self.events = events

    def add(self, paper_id: int, label: str, content: str) -> int:
        """暂存一条待归类内容（导入时调用）。"""
        return self.repo.add(paper_id, label, content)

    def list(self, paper_id: int | None = None) -> list[PendingContent]:
        """某篇论文（或全部）尚未归类的内容。"""
        return self.repo.list(paper_id)

    def assign(self, pending_id: int, field_id: int) -> None:
        """把一条待归类内容并入某个字段（追加到该字段已有内容之后）。"""
        p = self.repo.get(pending_id)
        if not p:
            return
        with self.papers.transaction():
            old = self.papers.get_field_text(p.paper_id, field_id)
            self.papers.set_field(p.paper_id, field_id, (old + "\n" + p.content).strip())
            self.repo.delete(pending_id)
        self.events.publish(Events.PAPER_CHANGED, paper_id=p.paper_id)

    def discard(self, pending_id: int) -> None:
        p = self.repo.get(pending_id)
        self.repo.delete(pending_id)
        if p:
            self.events.publish(Events.PAPER_CHANGED, paper_id=p.paper_id)
