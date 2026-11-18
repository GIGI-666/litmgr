"""界面动效的开关和窗口淡入。所有过渡都在 Qt 事件循环中完成。"""

from PySide6.QtCore import QAbstractAnimation, QEasingCurve, QObject, QPropertyAnimation, Qt, Signal
from PySide6.QtWidgets import QApplication, QWidget

FADE_DURATION_MS = 150
FADE_START_OPACITY = 0.76


class MotionPreference(QObject):
    """在同一进程的多个窗口间同步界面动画设置。"""

    changed = Signal(bool)

    def __init__(self, app: QApplication) -> None:
        super().__init__(app)
        self.enabled = True

    def set_enabled(self, enabled: bool) -> None:
        """更新设置，并通知现有窗口。"""
        if enabled != self.enabled:
            self.enabled = enabled
            self.changed.emit(enabled)


def motion_preference() -> MotionPreference:
    """返回当前应用共用的动画设置。"""
    app = QApplication.instance()
    preference = app.findChild(MotionPreference)
    if preference is None:
        preference = MotionPreference(app)
    return preference


def show_new_window(window: QWidget) -> None:
    """在 Windows 以窗口透明度淡入，显示和获取焦点无需等待动画结束。"""
    if (not motion_preference().enabled or QApplication.platformName() != "windows"
            or window.windowState() & Qt.WindowState.WindowMinimized):
        window.show()
        return
    animation = QPropertyAnimation(window, b"windowOpacity", window)
    animation.setDuration(FADE_DURATION_MS)
    animation.setStartValue(FADE_START_OPACITY)
    animation.setEndValue(1.0)
    animation.setEasingCurve(QEasingCurve.Type.OutCubic)
    motion_preference().changed.connect(animation.stop)
    # 正常播放和手动关闭动画都让窗口恢复完全不透明。
    animation.stateChanged.connect(
        lambda state: window.setWindowOpacity(1.0) if state == QAbstractAnimation.State.Stopped else None)
    window.setWindowOpacity(FADE_START_OPACITY)
    window.show()
    animation.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)
