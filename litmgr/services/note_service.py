"""笔记服务。

【作用】管理论文的阅读笔记/摘录（一篇论文多条），并让笔记内容可被全文检索。
【依赖】storage.note_repo / search_repo；core.events。
【被谁调用】ui.note_panel（详情窗口里的“笔记”页）。
"""

from __future__ import annotations

from ..core.errors import ValidationError
from ..core.events import EventBus, Events
from ..core.models import Note
from ..storage.note_repo import NoteRepo
from ..storage.search_repo import SearchRepo


class NoteService:
    def __init__(self, repo: NoteRepo, search_repo: SearchRepo, events: EventBus) -> None:
        self.repo = repo
        self.search = search_repo
        self.events = events

    def list(self, paper_id: int) -> list[Note]:
        return self.repo.list_for_paper(paper_id)

    def add(self, paper_id: int, content: str) -> int:
        if not content.strip():
            raise ValidationError("笔记内容不能为空")
        nid = self.repo.add(paper_id, content.strip())
        self._after(paper_id)
        return nid

    def update(self, note_id: int, paper_id: int, content: str) -> None:
        self.repo.update(note_id, content.strip())
        self._after(paper_id)

    def delete(self, note_id: int, paper_id: int) -> None:
        self.repo.delete(note_id)
        self._after(paper_id)

    def _after(self, paper_id: int) -> None:
        self.search.index_notes(paper_id, self.repo.all_text(paper_id))
        self.events.publish(Events.NOTES_CHANGED, paper_id=paper_id)
