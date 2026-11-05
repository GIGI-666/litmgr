"""阅读历史服务：最近阅读的论文 + 关闭时的页面状态。

【作用】记住最近阅读的 N 篇论文（默认 10 篇），并保存每篇关闭阅读窗口时的页面状态，
    以便点击历史记录就能还原到离开时的样子。
【职责】
    - record_open：打开阅读窗口时调用，刷新“最近阅读”顺序，超出 N 篇的最旧记录自动删除
    - save_state / get_state：保存/读取页面状态（一个字典，格式由界面层决定，本服务不解释）
    - recent：返回带标题的最近阅读列表，供菜单显示（已被删除的论文会自动忽略）
    - clear / remove：清空或单条移除
【事件】记录变化后发布 Events.READING_HISTORY_CHANGED，菜单据此刷新。
【依赖】storage.reading_repo；services.paper_service；core.events。
【被谁调用】ui.reader_window（打开/关闭时）、ui.main_window（“最近阅读”菜单）。
【扩展点】想保留更多篇：改 HISTORY_LIMIT；想多记状态项：只需改界面层的 capture_state。
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from ..core.events import EventBus, Events
from ..storage.reading_repo import ReadingRepo
from .paper_service import PaperService

log = logging.getLogger(__name__)

HISTORY_LIMIT = 10


@dataclass
class HistoryItem:
    paper_id: int
    title: str
    last_opened: str   # 形如 “2026-11-04 10:30:00”


class ReadingHistoryService:
    def __init__(self, repo: ReadingRepo, papers: PaperService, events: EventBus,
                 limit: int = HISTORY_LIMIT) -> None:
        self.repo, self.papers, self.events, self.limit = repo, papers, events, limit

    def record_open(self, paper_id: int) -> None:
        """记录“正在阅读这篇论文”，并裁剪到最近 limit 篇。"""
        self.repo.touch(paper_id)
        self.repo.trim(self.limit)
        self.events.publish(Events.READING_HISTORY_CHANGED)

    def save_state(self, paper_id: int, state: dict) -> None:
        """保存页面状态（不触发菜单刷新：顺序和标题都没变）。"""
        try:
            self.repo.save_state(paper_id, json.dumps(state, ensure_ascii=False))
        except (TypeError, ValueError):
            log.exception("阅读状态无法序列化，已忽略")

    def get_state(self, paper_id: int) -> dict:
        rec = self.repo.get(paper_id)
        if rec is None:
            return {}
        try:
            data = json.loads(rec.state_json or "{}")
        except ValueError:
            return {}
        return data if isinstance(data, dict) else {}

    def recent(self) -> list[HistoryItem]:
        items: list[HistoryItem] = []
        for rec in self.repo.list_recent(self.limit):
            if not self.papers.exists(rec.paper_id):
                continue
            items.append(HistoryItem(rec.paper_id, self.papers.get(rec.paper_id).title,
                                     rec.last_opened[:19]))
        return items

    def remove(self, paper_id: int) -> None:
        self.repo.remove(paper_id)
        self.events.publish(Events.READING_HISTORY_CHANGED)

    def clear(self) -> None:
        self.repo.clear()
        self.events.publish(Events.READING_HISTORY_CHANGED)
