"""字段编辑控件。

【作用】为每种字段类型提供合适的编辑控件（单行、多行、下拉、星级、链接……），
    详情窗口的字段表单据此为每个字段生成编辑器。
【统一接口】所有编辑器继承 FieldEditor：
    - set_text(text)   设置显示内容（不会触发 committed）
    - text()           取当前内容
    - committed(str)   用户“提交”时发出（失去焦点 / 回车 / 选择了下拉项）
【机制】控件通过注册表 EDITORS 与字段类型名关联；新增字段类型只需在
    core.field_types 注册类型，再在这里 EDITORS.register(类型名, 控件类) 即可。
    未注册的类型自动使用多行文本控件，因此永远不会显示不出来。
【依赖】PySide6；core.models.FieldDef；core.registry；ui.utils。
【被谁调用】ui.field_form（字段表单）。
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import (QComboBox, QHBoxLayout, QLineEdit, QPlainTextEdit, QPushButton,
                               QVBoxLayout, QWidget)

from ..core.models import FieldDef
from ..core.registry import Registry
from ..core.textutil import URL_RE
from .utils import open_url

class FieldEditor(QWidget):
    """字段编辑器基类。"""

    committed = Signal(str)

    def __init__(self, fdef: FieldDef, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.fdef = fdef
        self._last = ""   # 上一次已提交/设置的文本，用于避免无变化时重复提交

    def set_text(self, text: str) -> None:
        raise NotImplementedError

    def text(self) -> str:
        raise NotImplementedError

    def is_editing(self) -> bool:
        """用户正在输入时，外部刷新不应覆盖内容。"""
        return self.hasFocus() or any(w.hasFocus() for w in self.findChildren(QWidget))

    def _commit(self) -> None:
        t = self.text()
        if t != self._last:
            self._last = t
            self.committed.emit(t)

    def accept_normalized(self, text: str) -> None:
        """服务层返回规范化后的值（如日期格式化）时回写显示，同时更新“已提交”基准。"""
        self._last = text
        self.set_text(text)


class LineEditor(FieldEditor):
    """单行文本（也用于数字、日期、多标签）。"""

    def __init__(self, fdef, parent=None, placeholder: str = "") -> None:
        super().__init__(fdef, parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.edit = QLineEdit()
        self.edit.setPlaceholderText(placeholder)
        self.edit.editingFinished.connect(self._commit)
        lay.addWidget(self.edit)

    def set_text(self, text: str) -> None:
        self._last = text
        self.edit.setText(text)

    def text(self) -> str:
        return self.edit.text()


class DateEditor(LineEditor):
    def __init__(self, fdef, parent=None) -> None:
        super().__init__(fdef, parent, "如 2024-06-17、2024.6、2024（自动规范化）")


class TagsEditor(LineEditor):
    def __init__(self, fdef, parent=None) -> None:
        super().__init__(fdef, parent, "多个标签用逗号、顿号或分号分隔")


class NumberEditor(LineEditor):
    def __init__(self, fdef, parent=None) -> None:
        super().__init__(fdef, parent, "数字")


class _GrowingPlainText(QPlainTextEdit):
    """多行文本：失去焦点时发出 focusLost，高度随内容自适应（有上下限）。"""

    focusLost = Signal()

    def __init__(self, min_lines: int = 2, max_lines: int = 14) -> None:
        super().__init__()
        self._min_lines, self._max_lines = min_lines, max_lines
        self.setTabChangesFocus(True)
        self.document().documentLayout().documentSizeChanged.connect(self._fit)
        self._fit()

    def _fit(self) -> None:
        fm = QFontMetrics(self.font())
        lines = max(self._min_lines, min(self._max_lines, int(self.document().size().height()) + 1))
        self.setFixedHeight(lines * fm.lineSpacing() + 14)

    def resizeEvent(self, e) -> None:  # 宽度变化会改变折行数
        super().resizeEvent(e)
        self._fit()

    def focusOutEvent(self, e) -> None:
        super().focusOutEvent(e)
        self.focusLost.emit()


class TextEditor(FieldEditor):
    """长文本：多行、自适应高度。"""

    def __init__(self, fdef, parent=None) -> None:
        super().__init__(fdef, parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.edit = _GrowingPlainText()
        self.edit.focusLost.connect(self._commit)
        lay.addWidget(self.edit)
        self.extra = QHBoxLayout()
        self.extra.setContentsMargins(0, 0, 0, 0)
        lay.addLayout(self.extra)

    def set_text(self, text: str) -> None:
        self._last = text
        if self.edit.toPlainText() != text:
            self.edit.setPlainText(text)

    def text(self) -> str:
        return self.edit.toPlainText()


class UrlEditor(TextEditor):
    """链接：多行文本 + “打开”按钮（逐个打开其中的网址）。"""

    def __init__(self, fdef, parent=None) -> None:
        super().__init__(fdef, parent)
        self.btn = QPushButton("打开链接")
        self.btn.setToolTip("用浏览器打开文本中的所有网址")
        self.btn.clicked.connect(self._open)
        self.extra.addWidget(self.btn)
        self.extra.addStretch(1)

    def _open(self) -> None:
        for u in URL_RE.findall(self.text()):
            open_url(u)


class SelectEditor(FieldEditor):
    """单选：可编辑的下拉框，候选项来自字段定义，也允许输入候选项之外的值。"""

    def __init__(self, fdef, parent=None) -> None:
        super().__init__(fdef, parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.combo = QComboBox()
        self.combo.setEditable(True)
        self.combo.addItem("")
        self.combo.addItems(fdef.options)
        self.combo.activated.connect(lambda _i: self._commit())
        self.combo.lineEdit().editingFinished.connect(self._commit)
        lay.addWidget(self.combo)

    def set_text(self, text: str) -> None:
        self._last = text
        self.combo.setCurrentText(text)

    def text(self) -> str:
        return self.combo.currentText()


class RatingEditor(FieldEditor):
    """星级 0-5。"""

    def __init__(self, fdef, parent=None) -> None:
        super().__init__(fdef, parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.combo = QComboBox()
        self.combo.addItem("未评分", "")
        for n in range(1, 6):
            self.combo.addItem("★" * n + "☆" * (5 - n), str(n))
        self.combo.activated.connect(lambda _i: self._commit())
        lay.addWidget(self.combo, 0, Qt.AlignLeft)

    def set_text(self, text: str) -> None:
        self._last = text
        i = self.combo.findData(text)
        self.combo.setCurrentIndex(max(i, 0))

    def text(self) -> str:
        return self.combo.currentData() or ""


EDITORS: Registry[type[FieldEditor]] = Registry("字段编辑控件")
EDITORS.register("text", LineEditor)
EDITORS.register("longtext", TextEditor)
EDITORS.register("select", SelectEditor)
EDITORS.register("tags", TagsEditor)
EDITORS.register("number", NumberEditor)
EDITORS.register("date", DateEditor)
EDITORS.register("rating", RatingEditor)
EDITORS.register("url", UrlEditor)


def create_editor(fdef: FieldDef, parent: QWidget | None = None) -> FieldEditor:
    """按字段类型创建编辑器；类型未注册则回退为多行文本。"""
    cls = EDITORS.get(fdef.type) if fdef.type in EDITORS else TextEditor
    return cls(fdef, parent)
