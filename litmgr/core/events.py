"""事件总线（发布/订阅）。

【作用】让模块之间通过“事件”通信而不是互相直接调用，实现低耦合。
    例如：字段值被修改后，服务层发布 PAPER_CHANGED，所有打开的详情窗口、
    列表、对比窗口各自订阅并自行刷新，彼此互不知晓。
【职责】
    - subscribe：订阅某个事件
    - publish：发布事件，同步调用所有订阅者
    - 提供全部事件名常量（避免到处写魔法字符串）
【依赖】无。
【被谁调用】services 发布事件；ui 订阅事件。
【扩展点】新增事件只需在 Events 类里加一个常量。
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Callable

log = logging.getLogger(__name__)


class Events:
    """所有事件名常量。payload 约定写在注释里。"""

    PAPER_ADDED = "paper_added"          # paper_id
    PAPER_CHANGED = "paper_changed"      # paper_id（字段值/状态/标签等任何变化）
    PAPER_DELETED = "paper_deleted"      # paper_id
    FIELDS_CHANGED = "fields_changed"    # 字段定义增删改（列表、详情需重建表单）
    LIST_COLUMNS_CHANGED = "list_columns_changed"  # 论文列表的显示列变化（只需刷新列表）
    FILES_CHANGED = "files_changed"      # paper_id（论文文件增删）
    ORGANIZE_CHANGED = "organize_changed"  # 标签/分组/保存的检索变化
    NOTES_CHANGED = "notes_changed"      # paper_id
    LIBRARY_CHANGED = "library_changed"  # 批量导入、恢复备份等，需整体刷新
    READING_HISTORY_CHANGED = "reading_history_changed"  # 最近阅读列表变化（无 payload）


class EventBus:
    """同步事件总线。单线程 GUI 程序足够使用。"""

    def __init__(self) -> None:
        self._handlers: dict[str, list[Callable[..., None]]] = defaultdict(list)

    def subscribe(self, event: str, handler: Callable[..., None]) -> None:
        """订阅事件。handler 以关键字参数接收 payload。"""
        if handler not in self._handlers[event]:
            self._handlers[event].append(handler)

    def unsubscribe(self, event: str, handler: Callable[..., None]) -> None:
        """取消订阅（窗口关闭时应调用，避免对已销毁对象回调）。"""
        if handler in self._handlers.get(event, []):
            self._handlers[event].remove(handler)

    def publish(self, event: str, **payload: Any) -> None:
        """发布事件。某个订阅者出错不会影响其他订阅者。"""
        for handler in list(self._handlers.get(event, [])):
            try:
                handler(**payload)
            except Exception:  # noqa: BLE001 - 订阅者错误不能拖垮发布者
                log.exception("事件 %s 的订阅者 %r 执行出错", event, handler)
