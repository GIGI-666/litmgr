"""界面层通用工具。

【作用】放各窗口都会用到的小工具，避免重复代码：
    - open_path / open_url：用系统默认程序打开文件/链接
    - guarded：装饰器，捕获业务异常并弹窗提示，而不是让程序崩溃
    - EventSubscriberMixin：窗口订阅事件总线，并在关闭时自动取消订阅（防止对已销毁窗口回调）
    - apply_app_style：全局样式（含下拉框悬停绘制，避免高亮盖住文字）
【依赖】PySide6；core.errors / core.events。
【被谁调用】ui 下几乎所有模块。
"""

from __future__ import annotations

import functools
import logging
import traceback
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QEvent, QObject, Qt, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QFont, QPainter
from PySide6.QtWidgets import (QApplication, QComboBox, QHBoxLayout, QMessageBox, QPushButton,
                               QStyle, QStyleOptionViewItem, QStyledItemDelegate, QWidget)

from ..core.errors import LitmgrError
from ..core.events import EventBus

log = logging.getLogger(__name__)


def open_path(path: Path | str) -> None:
    """用系统默认程序打开本地文件。"""
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))


def open_url(url: str) -> None:
    QDesktopServices.openUrl(QUrl(url))


def show_error(parent: QWidget | None, text: str, title: str = "操作失败") -> None:
    QMessageBox.warning(parent, title, text)


def make_button(text: str, fn: Callable[[], None], tooltip: str = "") -> QPushButton:
    """创建按钮并连接无参回调。

    直接写 clicked.connect(fn) 时，Qt 会把 checked 参数传给 fn，导致带默认参数的回调
    收到错误的值；这里统一吞掉该参数，全工程的按钮都用它创建。
    """
    b = QPushButton(text)
    if tooltip:
        b.setToolTip(tooltip)
    b.clicked.connect(lambda _checked=False: fn())
    return b


def add_buttons(layout, specs: list[tuple[str, Callable[[], None]]], *, stretch: bool = True) -> list:
    """在 layout 里加一行按钮。specs: [(按钮文字, 回调), ...]；stretch=True 时按钮靠左排列。"""
    row = QHBoxLayout()
    buttons = []
    for text, fn in specs:
        b = make_button(text, fn)
        row.addWidget(b)
        buttons.append(b)
    if stretch:
        row.addStretch(1)
    layout.addLayout(row)
    return buttons


def guarded(fn: Callable) -> Callable:
    """装饰窗口方法：业务异常（LitmgrError）弹出友好提示；其他异常记录日志并提示，不崩溃。"""

    @functools.wraps(fn)
    def wrapper(self, *args, **kwargs):
        try:
            return fn(self, *args, **kwargs)
        except LitmgrError as e:
            show_error(self if isinstance(self, QWidget) else None, str(e))
        except Exception as e:  # noqa: BLE001
            log.error("未处理的错误\n%s", traceback.format_exc())
            show_error(self if isinstance(self, QWidget) else None, f"发生意外错误：{e}")
        return None

    return wrapper


class EventSubscriberMixin:
    """混入窗口类：用 self.subscribe(bus, 事件, 处理函数) 订阅；窗口关闭时调用 unsubscribe_all()。"""

    _subs: list

    def subscribe(self, bus: EventBus, event: str, handler: Callable[..., None]) -> None:
        if not hasattr(self, "_subs"):
            self._subs = []
        bus.subscribe(event, handler)
        self._subs.append((bus, event, handler))

    def unsubscribe_all(self) -> None:
        for bus, event, handler in getattr(self, "_subs", []):
            bus.unsubscribe(event, handler)
        self._subs = []


class _ComboItemDelegate(QStyledItemDelegate):
    """组合框下拉项：悬停只在文字后面画浅色圆角底，文字画在最上层。

    全局样式作用到 QComboBox 后，系统会把悬停高亮画在文字上面，选项字会被挡住。
    这里改为自己绘制，高亮不再盖住字形。
    """

    def sizeHint(self, option, index):
        hint = super().sizeHint(option, index)
        if hint.height() < 30:
            hint.setHeight(30)
        return hint

    def paint(self, painter, option, index) -> None:
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(opt.rect, QColor("#ffffff"))
        hovered = bool(opt.state & QStyle.StateFlag.State_MouseOver)
        selected = bool(opt.state & QStyle.StateFlag.State_Selected)
        enabled = bool(opt.state & QStyle.StateFlag.State_Enabled)
        if hovered or selected:
            # 阴影留在本行内部，不压到相邻选项的文字
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 0, 0, 28))
            painter.drawRoundedRect(opt.rect.adjusted(6, 4, -4, -1), 4, 4)
            painter.setPen(QColor("#d4e3f6"))
            painter.setBrush(QColor("#f4f8fd" if hovered else "#e7f0fb"))
            painter.drawRoundedRect(opt.rect.adjusted(4, 2, -4, -2), 4, 4)
        text_rect = opt.rect.adjusted(12, 0, -10, 0)
        painter.setPen(QColor("#222222" if enabled else "#999999"))
        painter.setFont(opt.font)
        text = opt.fontMetrics.elidedText(
            opt.text, Qt.TextElideMode.ElideRight, max(0, text_rect.width()))
        painter.drawText(text_rect, int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft), text)
        painter.restore()


class _ComboPopupFix(QObject):
    """给之后出现的每一个组合框换上上面的绘制器。"""

    def eventFilter(self, obj, event) -> bool:
        if event.type() == QEvent.Type.Show and isinstance(obj, QComboBox):
            view = obj.view()
            if not isinstance(view.itemDelegate(), _ComboItemDelegate):
                view.setItemDelegate(_ComboItemDelegate(view))
                view.setMouseTracking(True)
        return False


def apply_app_style(app: QApplication) -> None:
    """全局字体与样式：中文友好、紧凑、表格行交替色。"""
    app.setStyle("Fusion")
    font = QFont("Microsoft YaHei UI", 10)
    app.setFont(font)
    app.setStyleSheet("""
        QTableView { alternate-background-color: #f6f8fb; gridline-color: #e3e7ee; }
        QTableView::item:selected { background: #cfe3ff; color: black; }
        QHeaderView::section { background: #eef1f6; padding: 4px 6px; border: 0;
                               border-right: 1px solid #dde2ea; border-bottom: 1px solid #dde2ea; }
        QGroupBox { font-weight: bold; border: 1px solid #d6dbe4; border-radius: 4px;
                    margin-top: 10px; padding-top: 8px; }
        QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
        QPlainTextEdit, QLineEdit { border: 1px solid #c9d0db; border-radius: 3px;
                                    padding: 2px 4px; background: white; }
        QComboBox { border: 1px solid #c9d0db; border-radius: 3px;
                    padding: 2px 8px 2px 6px; background: white; color: #222; }
        QComboBox:focus { border: 1px solid #4a90e2; }
        QComboBox QAbstractItemView { background: white; color: #222; outline: 0;
                                      border: 1px solid #d0d7e2;
                                      selection-background-color: transparent;
                                      selection-color: #222; }
        QComboBox QAbstractItemView::item { color: #222; background: transparent;
                                            min-height: 30px; padding: 4px 10px; }
        QComboBox QAbstractItemView::item:hover,
        QComboBox QAbstractItemView::item:selected { background: transparent; color: #222; }
        QPlainTextEdit:focus, QLineEdit:focus { border: 1px solid #4a90e2; }
        QToolBar { spacing: 4px; }
    """)
    fixer = _ComboPopupFix(app)
    app.installEventFilter(fixer)
    app._litmgr_combo_fix = fixer  # 挂在 app 上，避免被回收
