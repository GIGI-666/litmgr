"""高级过滤对话框。

【作用】设置“按字段条件过滤”：可添加多条条件（字段 + 操作 + 值），全部满足才显示；
    另可限定阅读状态、最低星级、是否包含已归档论文。
    可用的操作随字段类型变化（日期有“晚于/早于”，标签有“含有标签”等）。
【依赖】core.field_types（操作列表）；services.search_service（SearchQuery / Condition）。
【被谁调用】ui.main_window（“高级过滤”按钮）。
"""

from __future__ import annotations

from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout,
                               QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget)

from ..core.field_types import OP_EMPTY, OP_LABELS, OP_NOT_EMPTY, get_type
from ..core.models import READ_STATUS
from ..services.app_context import AppContext
from ..services.search_service import Condition, SearchQuery


class _ConditionRow(QWidget):
    def __init__(self, ctx: AppContext, cond: Condition | None = None) -> None:
        super().__init__()
        self.fields = ctx.fields.list()
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        self.field_box = QComboBox()
        for f in self.fields:
            self.field_box.addItem(f.name, f.id)
        self.op_box = QComboBox()
        self.value = QLineEdit()
        self.remove_btn = QPushButton("×")
        self.remove_btn.setFixedWidth(28)
        for w in (self.field_box, self.op_box, self.value, self.remove_btn):
            h.addWidget(w)
        h.setStretch(2, 1)
        self.field_box.currentIndexChanged.connect(self._reload_ops)
        self.op_box.currentIndexChanged.connect(self._toggle_value)
        if cond:
            self.field_box.setCurrentIndex(max(self.field_box.findData(cond.field_id), 0))
        self._reload_ops()
        if cond:
            self.op_box.setCurrentIndex(max(self.op_box.findData(cond.op), 0))
            self.value.setText(cond.value)

    def _reload_ops(self) -> None:
        f = self.fields[self.field_box.currentIndex()] if self.fields else None
        self.op_box.blockSignals(True)
        self.op_box.clear()
        if f:
            for op in get_type(f.type).ops:
                self.op_box.addItem(OP_LABELS[op], op)
        self.op_box.blockSignals(False)
        self._toggle_value()

    def _toggle_value(self) -> None:
        self.value.setEnabled(self.op_box.currentData() not in (OP_EMPTY, OP_NOT_EMPTY))

    def condition(self) -> Condition | None:
        if not self.fields or self.op_box.currentData() is None:
            return None
        return Condition(self.field_box.currentData(), self.op_box.currentData(), self.value.text())


class FilterDialog(QDialog):
    def __init__(self, parent, ctx: AppContext, query: SearchQuery) -> None:
        super().__init__(parent)
        self.ctx = ctx
        self.setWindowTitle("高级过滤")
        self.resize(640, 440)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("字段条件（全部满足才显示）："))
        self.rows_box = QVBoxLayout()
        lay.addLayout(self.rows_box)
        add = QPushButton("＋ 添加条件")
        add.clicked.connect(lambda: self._add_row(None))
        lay.addWidget(add)
        for c in query.conditions:
            self._add_row(c)
        form = QFormLayout()
        self.status = QComboBox()
        self.status.addItem("不限", None)
        for k, v in READ_STATUS.items():
            self.status.addItem(v, k)
        self.status.setCurrentIndex(max(self.status.findData(query.read_status), 0))
        self.rating = QComboBox()
        self.rating.addItem("不限", 0)
        for n in range(1, 6):
            self.rating.addItem(f"≥ {n} 星", n)
        self.rating.setCurrentIndex(max(self.rating.findData(query.min_rating), 0))
        self.archived = QCheckBox("包含已归档的论文")
        self.archived.setChecked(query.include_archived)
        form.addRow("阅读状态：", self.status)
        form.addRow("星级：", self.rating)
        form.addRow("", self.archived)
        lay.addLayout(form)
        lay.addStretch(1)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        clear = bb.addButton("清除全部条件", QDialogButtonBox.ResetRole)
        clear.clicked.connect(self._clear)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def _add_row(self, cond: Condition | None) -> None:
        row = _ConditionRow(self.ctx, cond)
        row.remove_btn.clicked.connect(lambda: (self.rows_box.removeWidget(row), row.deleteLater()))
        self.rows_box.addWidget(row)

    def _clear(self) -> None:
        while self.rows_box.count():
            w = self.rows_box.takeAt(0).widget()
            if w:
                w.deleteLater()
        self.status.setCurrentIndex(0)
        self.rating.setCurrentIndex(0)

    def apply_to(self, query: SearchQuery) -> None:
        """把对话框里的设置写回 query。"""
        conds = []
        for i in range(self.rows_box.count()):
            w = self.rows_box.itemAt(i).widget()
            if isinstance(w, _ConditionRow) and (c := w.condition()):
                conds.append(c)
        query.conditions = conds
        query.read_status = self.status.currentData()
        query.min_rating = self.rating.currentData()
        query.include_archived = self.archived.isChecked()
