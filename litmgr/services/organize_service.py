"""整理服务：标签、分组、保存的检索。

【作用】帮助用户把论文归类整理：给论文打标签、放进分组（一篇论文可属多个分组）、
    保存常用的检索条件以便一键复用。阅读状态/星级的修改在 paper_service。
【职责】增删改标签/分组/保存的检索，修改后发布 ORGANIZE_CHANGED / PAPER_CHANGED 事件。
【依赖】storage.organize_repo；core.events；core.errors。
【被谁调用】ui.organize_panel / main_window 侧栏 / detail_window。
【扩展点】要增加新的整理维度（如“项目”），仿照分组在 organize_repo 与此处各加一组方法。
"""

from __future__ import annotations

import sqlite3

from ..core.errors import DuplicateError, ValidationError
from ..core.events import EventBus, Events
from ..core.models import Collection, SavedView, Tag
from ..core.query import SearchQuery
from ..storage.organize_repo import OrganizeRepo


class OrganizeService:
    def __init__(self, repo: OrganizeRepo, events: EventBus) -> None:
        self.repo = repo
        self.events = events

    # ---------- 标签 ----------
    def tags(self) -> list[Tag]:
        return self.repo.list_tags()

    def tag_counts(self) -> dict[int, int]:
        return self.repo.tag_counts()

    def tags_of(self, paper_id: int) -> list[Tag]:
        return self.repo.tags_of_paper(paper_id)

    def tag_map(self) -> dict[int, list[str]]:
        return self.repo.tag_map()

    def get_or_create_tag(self, name: str) -> Tag:
        name = name.strip()
        if not name:
            raise ValidationError("标签名不能为空")
        t = self.repo.find_tag(name)
        if t:
            return t
        tid = self.repo.add_tag(name)
        self.events.publish(Events.ORGANIZE_CHANGED)
        return Tag(tid, name)

    def tag_papers(self, paper_ids: list[int], name: str) -> None:
        t = self.get_or_create_tag(name)
        with self.repo.db.transaction():
            for pid in paper_ids:
                self.repo.attach_tag(pid, t.id)
        for pid in paper_ids:
            self.events.publish(Events.PAPER_CHANGED, paper_id=pid)
        self.events.publish(Events.ORGANIZE_CHANGED)

    def untag_paper(self, paper_id: int, tag_id: int) -> None:
        self.repo.detach_tag(paper_id, tag_id)
        self.events.publish(Events.PAPER_CHANGED, paper_id=paper_id)
        self.events.publish(Events.ORGANIZE_CHANGED)

    def rename_tag(self, tag_id: int, name: str) -> None:
        self._guard(lambda: self.repo.rename_tag(tag_id, name.strip()), "标签")
        self.events.publish(Events.ORGANIZE_CHANGED)

    def delete_tag(self, tag_id: int) -> None:
        self.repo.delete_tag(tag_id)
        # 主窗口与详情窗口都订阅 ORGANIZE_CHANGED（刷新侧栏、列表、标签条），不必整库刷新
        self.events.publish(Events.ORGANIZE_CHANGED)

    # ---------- 分组 ----------
    def collections(self) -> list[Collection]:
        return self.repo.list_collections()

    def collection_counts(self) -> dict[int, int]:
        return self.repo.collection_counts()

    def collections_of(self, paper_id: int) -> list[Collection]:
        return self.repo.collections_of_paper(paper_id)

    def add_collection(self, name: str) -> int:
        name = name.strip()
        if not name:
            raise ValidationError("分组名不能为空")
        cid = self._guard(lambda: self.repo.add_collection(name), "分组")
        self.events.publish(Events.ORGANIZE_CHANGED)
        return cid

    def rename_collection(self, cid: int, name: str) -> None:
        self._guard(lambda: self.repo.rename_collection(cid, name.strip()), "分组")
        self.events.publish(Events.ORGANIZE_CHANGED)

    def delete_collection(self, cid: int) -> None:
        self.repo.delete_collection(cid)
        self.events.publish(Events.ORGANIZE_CHANGED)

    def add_to_collection(self, paper_ids: list[int], cid: int, *, publish: bool = True) -> None:
        with self.repo.db.transaction():
            for pid in paper_ids:
                self.repo.add_to_collection(pid, cid)
        if publish:
            for pid in paper_ids:
                self.events.publish(Events.PAPER_CHANGED, paper_id=pid)
            self.events.publish(Events.ORGANIZE_CHANGED)

    def remove_from_collection(self, paper_id: int, cid: int) -> None:
        self.repo.remove_from_collection(paper_id, cid)
        self.events.publish(Events.PAPER_CHANGED, paper_id=paper_id)
        self.events.publish(Events.ORGANIZE_CHANGED)

    # ---------- 保存的检索 ----------
    def views(self) -> list[SavedView]:
        return self.repo.list_views()

    def save_view(self, name: str, query: SearchQuery) -> int:
        name = name.strip()
        if not name:
            raise ValidationError("名称不能为空")
        vid = self.repo.save_view(name, query.to_dict())
        self.events.publish(Events.ORGANIZE_CHANGED)
        return vid

    def delete_view(self, vid: int) -> None:
        self.repo.delete_view(vid)
        self.events.publish(Events.ORGANIZE_CHANGED)

    @staticmethod
    def query_of(view: SavedView) -> SearchQuery:
        return SearchQuery.from_dict(view.query)

    @staticmethod
    def _guard(fn, what: str):
        try:
            return fn()
        except sqlite3.IntegrityError:
            raise DuplicateError(f"该{what}名称已存在") from None
