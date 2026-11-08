"""字段管理对话框。

【作用】管理论文卡片的字段：新增、编辑（改名/改类型/候选项/别名/分组/是否在列表显示）、
    拖动调整顺序、归档与恢复、永久删除。所有论文共用同一套字段，修改后各窗口自动刷新。
【要点】
    - 可按分组筛选字段，从“管理分组”新建、改名或删除字段分组。
    - “归档”只是隐藏字段，数据保留，可随时恢复；“永久删除”只对已归档字段开放。
    - 改类型前会预览有多少值会被规范化/无法按新类型解析（原文始终保留，不丢数据）。
    - 别名：导入卡片时，卡片里写成别名的字段名也会被识别为这个字段。
【依赖】services.field_service（通过 AppContext）；core.field_types（类型列表）。
【被谁调用】ui.main_window（“字段管理”菜单）。
【扩展点】单字段编辑在 FieldEditDialog，分组整体管理在 ui.field_group_dialog。
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                               QFormLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QMessageBox, QPlainTextEdit, QVBoxLayout)

from ..core.field_types import FIELD_TYPES
from ..core.models import FieldDef
from ..services.app_context import AppContext
from .field_group_dialog import FieldGroupDialog
from .utils import add_buttons, guarded, make_button


class FieldEditDialog(QDialog):
    """新增/编辑单个字段。"""

    def __init__(self, parent, ctx: AppContext, fdef: FieldDef | None,
                 default_group: str = "") -> None:
        super().__init__(parent)
        self.ctx, self.fdef = ctx, fdef
        self.setWindowTitle("编辑字段" if fdef else "新增字段")
        self.resize(460, 480)
        form = QFormLayout(self)
        self.name = QLineEdit(fdef.name if fdef else "")
        self.type = QComboBox()
        for t in FIELD_TYPES.values():
            self.type.addItem(t.label, t.name)
        self.type.setCurrentIndex(max(self.type.findData(fdef.type if fdef else "longtext"), 0))
        self.group = QComboBox()
        self.group.setEditable(True)
        self.group.addItem("未分组")
        self.group.addItems(ctx.fields.groups())
        self.group.setCurrentText((fdef.group_name if fdef else default_group) or "未分组")
        self.options = QPlainTextEdit("\n".join(fdef.options) if fdef else "")
        self.options.setPlaceholderText("单选字段的候选项，每行一个（也允许输入候选之外的值）")
        self.aliases = QPlainTextEdit("\n".join(fdef.aliases) if fdef else "")
        self.aliases.setPlaceholderText("别名，每行一个。导入卡片时，写成别名的字段名也会识别为本字段")
        self.show_in_list = QCheckBox("在论文列表中显示这一列")
        self.show_in_list.setChecked(fdef.show_in_list if fdef else False)
        form.addRow("字段名：", self.name)
        form.addRow("类型：", self.type)
        form.addRow("分组：", self.group)
        form.addRow("候选项：", self.options)
        form.addRow("别名：", self.aliases)
        form.addRow("", self.show_in_list)
        if fdef and fdef.role:
            form.addRow("", QLabel(f"（系统角色：{fdef.role}，改名不影响该功能）"))
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        form.addRow(bb)

    @staticmethod
    def _lines(box: QPlainTextEdit) -> list[str]:
        return [x.strip() for x in box.toPlainText().splitlines() if x.strip()]

    @guarded
    def accept(self) -> None:
        new_type = self.type.currentData()
        group_name = self.group.currentText().strip()
        if group_name == "未分组":
            group_name = ""
        if self.fdef:
            if new_type != self.fdef.type:
                changed, unparsed = self.ctx.fields.preview_type_change(self.fdef.id, new_type)
                msg = (f"类型将从“{self.fdef.type}”改为“{new_type}”。\n"
                       f"约 {changed} 个值会被规范化改写，{unparsed} 个值无法按新类型解析（将保留原文）。\n"
                       "原文本内容不会丢失。继续？")
                if QMessageBox.question(self, "修改字段类型", msg) != QMessageBox.Yes:
                    return
            f = self.fdef
            f.name, f.type = self.name.text(), new_type
            f.group_name = group_name
            f.options, f.aliases = self._lines(self.options), self._lines(self.aliases)
            f.show_in_list = self.show_in_list.isChecked()
            self.ctx.fields.update(f)
        else:
            self.ctx.fields.add(self.name.text(), new_type, options=self._lines(self.options),
                                aliases=self._lines(self.aliases),
                                group_name=group_name,
                                show_in_list=self.show_in_list.isChecked())
        super().accept()


class FieldManagerDialog(QDialog):
    """按分组筛选、增改字段，并提供字段分组管理入口。"""

    def __init__(self, parent, ctx: AppContext) -> None:
        super().__init__(parent)
        self.ctx = ctx
        self.setWindowTitle("字段管理")
        self.resize(560, 620)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("拖动调整字段顺序（影响详情页与对比窗口）；双击编辑。"))
        group_bar = QHBoxLayout()
        group_bar.addWidget(QLabel("字段分组："))
        self.group_filter = QComboBox()
        self.group_filter.currentIndexChanged.connect(lambda _i: self.refresh())
        group_bar.addWidget(self.group_filter, 1)
        group_bar.addWidget(make_button("管理分组…", self.manage_groups))
        lay.addLayout(group_bar)
        self.list = QListWidget()
        self.list.setDragDropMode(QAbstractItemView.InternalMove)
        self.list.model().rowsMoved.connect(self._on_moved)
        self.list.itemDoubleClicked.connect(lambda *_: self.edit())
        lay.addWidget(self.list)
        self.show_archived = QCheckBox("显示已归档字段")
        self.show_archived.toggled.connect(lambda _=None: self.refresh())
        lay.addWidget(self.show_archived)
        add_buttons(lay, [("新增字段", self.add), ("编辑", self.edit),
                          ("归档/恢复", self.toggle_archive), ("永久删除", self.delete)])
        self.refresh()

    def refresh(self) -> None:
        """更新分组筛选及字段列表；筛选时禁用拖动，避免扰乱全局顺序。"""
        selected_group = self.group_filter.currentData()
        self.group_filter.blockSignals(True)
        self.group_filter.clear()
        self.group_filter.addItem("全部分组", None)
        self.group_filter.addItem("未分组", "")
        for group in self.ctx.fields.groups():
            self.group_filter.addItem(group, group)
        self.group_filter.setCurrentIndex(max(0, self.group_filter.findData(selected_group)))
        self.group_filter.blockSignals(False)
        selected_group = self.group_filter.currentData()
        self.list.setDragDropMode(QAbstractItemView.InternalMove if selected_group is None
                                  else QAbstractItemView.NoDragDrop)
        current = self.list.currentItem()
        selected_id = current.data(Qt.UserRole) if current else None
        self.list.blockSignals(True)
        self.list.clear()
        for f in self.ctx.fields.list(include_archived=self.show_archived.isChecked()):
            if selected_group is not None and f.group_name != selected_group:
                continue
            text = f"{f.name}    [{f.type}]  {f.group_name or '未分组'}" + ("    （已归档）" if f.archived else "")
            it = QListWidgetItem(text)
            it.setData(Qt.UserRole, f.id)
            if f.archived:
                it.setForeground(Qt.gray)
            self.list.addItem(it)
            if f.id == selected_id:
                self.list.setCurrentItem(it)
        self.list.blockSignals(False)

    @guarded
    def manage_groups(self) -> None:
        """打开组名管理；关闭后同步空分组、改名和删除结果。"""
        FieldGroupDialog(self, self.ctx).exec()
        self.refresh()

    def _current(self) -> FieldDef | None:
        it = self.list.currentItem()
        return self.ctx.fields.get(it.data(Qt.UserRole)) if it else None

    @guarded
    def _on_moved(self, *_a) -> None:
        ids = [self.list.item(i).data(Qt.UserRole) for i in range(self.list.count())]
        self.ctx.fields.reorder(ids)

    @guarded
    def add(self) -> None:
        if FieldEditDialog(self, self.ctx, None,
                           default_group=self.group_filter.currentData() or "").exec() == QDialog.Accepted:
            self.refresh()

    @guarded
    def edit(self) -> None:
        f = self._current()
        if f and FieldEditDialog(self, self.ctx, f).exec() == QDialog.Accepted:
            self.refresh()

    @guarded
    def toggle_archive(self) -> None:
        f = self._current()
        if not f:
            return
        if f.archived:
            self.ctx.fields.restore(f.id)
        else:
            self.ctx.fields.archive(f.id)
        self.refresh()

    @guarded
    def delete(self) -> None:
        f = self._current()
        if not f:
            return
        if not f.archived:
            QMessageBox.information(self, "永久删除", "请先归档该字段，再永久删除。")
            return
        if QMessageBox.question(
                self, "永久删除字段",
                f"永久删除字段“{f.name}”及所有论文中的该字段内容？\n此操作不可恢复！") == QMessageBox.Yes:
            self.ctx.fields.delete_permanently(f.id)
            self.refresh()
