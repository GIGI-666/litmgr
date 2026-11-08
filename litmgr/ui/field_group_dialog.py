"""字段分组管理对话框。

【作用】新建、重命名和删除卡片的字段分组，例如“概要”“基本信息”。
【职责】展示各分组的字段数量并收集用户输入；删除只取消字段归属，保留论文内容。
【依赖】services.field_service（通过 AppContext）；ui.utils 的按钮工厂和异常提示。
【被谁调用】ui.field_manager_dialog，不涉及主窗口左侧的论文分组。
【扩展点】新增分组操作时在本窗口增加入口，校验和事务仍交给服务层。
"""

from __future__ import annotations

import html
from collections import Counter

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QInputDialog, QLabel,
                               QListWidget, QListWidgetItem, QMessageBox, QVBoxLayout)

from ..services.app_context import AppContext
from .utils import add_buttons, guarded


class FieldGroupDialog(QDialog):
    """管理全库共用的字段分组；空分组可提前建立，供新增字段时选择。"""

    def __init__(self, parent, ctx: AppContext) -> None:
        super().__init__(parent)
        self.ctx = ctx
        self.setWindowTitle("字段分组管理")
        self.resize(480, 420)
        lay = QVBoxLayout(self)
        hint = QLabel("管理卡片中的字段分组。删除分组后，其中字段移到“未分组”，内容保留。")
        hint.setWordWrap(True)
        lay.addWidget(hint)
        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(lambda *_: self.rename())
        self.list.currentItemChanged.connect(lambda *_: self._update_buttons())
        lay.addWidget(self.list)
        buttons = add_buttons(lay, [("新建分组", self.add), ("重命名分组", self.rename),
                                    ("删除分组", self.delete)])
        self.rename_btn, self.delete_btn = buttons[1:]
        close = QDialogButtonBox(QDialogButtonBox.Close)
        close.button(QDialogButtonBox.Close).setText("关闭")
        close.rejected.connect(self.reject)
        lay.addWidget(close)
        self.refresh()

    def refresh(self, selected: str | None = None) -> None:
        """刷新组名与字段计数，尽量保持选中分组。"""
        selected = selected if selected is not None else self._current()
        counts = Counter(f.group_name for f in self.ctx.fields.list(include_archived=True))
        self.list.clear()
        for group in self.ctx.fields.groups():
            item = QListWidgetItem(f"{group}    （{counts[group]} 个字段，含已归档）")
            item.setData(Qt.UserRole, group)
            self.list.addItem(item)
            if group == selected:
                self.list.setCurrentItem(item)
        self._update_buttons()

    def _current(self) -> str | None:
        item = self.list.currentItem()
        return item.data(Qt.UserRole) if item else None

    def _update_buttons(self) -> None:
        enabled = self._current() is not None
        self.rename_btn.setEnabled(enabled)
        self.delete_btn.setEnabled(enabled)

    @guarded
    def add(self) -> None:
        """收集组名并新建空分组。"""
        name, ok = QInputDialog.getText(self, "新建字段分组", "分组名称：")
        if ok:
            self.refresh(self.ctx.fields.add_group(name))

    @guarded
    def rename(self) -> None:
        """重命名选中分组，由服务层同步更新组内字段。"""
        group = self._current()
        if group is None:
            return
        name, ok = QInputDialog.getText(self, "重命名字段分组", "新的分组名称：", text=group)
        if ok:
            self.refresh(self.ctx.fields.rename_group(group, name))

    @guarded
    def delete(self) -> None:
        """确认后仅删除分组，保留其全部字段和论文内容。"""
        group = self._current()
        if group is None:
            return
        if QMessageBox.question(
                self, "删除字段分组",
                f"删除分组“{html.escape(group)}”？\n其中的字段将移到“未分组”，"
                "字段及所有论文中的内容都会保留。") == QMessageBox.Yes:
            self.ctx.fields.delete_group(group)
            self.refresh()
