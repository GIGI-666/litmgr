"""通用注册表。

【作用】提供“按名字注册、按名字取用”的容器，是系统可插拔的基础。
    字段类型、导出器、详情页面板、插件等都通过 Registry 接入：
    新增功能 = 新增一个文件并 register，不需要改动已有代码。
【依赖】无。
【被谁调用】core.field_types（字段类型）、services.export_service（导出器）、
    ui.detail_window（详情面板）、plugins。
"""

from __future__ import annotations

from typing import Generic, Iterator, TypeVar

T = TypeVar("T")


class Registry(Generic[T]):
    """名字 -> 对象 的有序注册表。"""

    def __init__(self, kind: str) -> None:
        self.kind = kind  # 用于错误提示，如 "字段类型"
        self._items: dict[str, T] = {}

    def register(self, name: str, item: T, *, replace: bool = False) -> T:
        """注册。默认不允许同名覆盖，避免插件之间悄悄冲突。"""
        if name in self._items and not replace:
            raise KeyError(f"{self.kind} 已存在: {name}")
        self._items[name] = item
        return item

    def get(self, name: str) -> T:
        try:
            return self._items[name]
        except KeyError:
            raise KeyError(f"未注册的{self.kind}: {name}") from None

    def __contains__(self, name: str) -> bool:
        return name in self._items

    def names(self) -> list[str]:
        return list(self._items)

    def items(self) -> Iterator[tuple[str, T]]:
        return iter(self._items.items())

    def values(self) -> list[T]:
        return list(self._items.values())
