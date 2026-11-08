"""应用图标及 Windows 任务栏身份配置。

【作用】让主窗口、详情、阅读器和任务栏共用 litmgr 自己的图标。
【职责】读取仓库内多尺寸 ICO，缺失时回退 SVG；Windows 显式区分 Python 宿主与本应用。
【依赖】PySide6.QtGui/QtWidgets、标准库 ctypes/pathlib/sys，不读写用户文献数据。
【被谁调用】litmgr.__main__ 创建 QApplication 后、创建任何业务窗口前调用。
【扩展点】替换图标时更新 assets/app-icon.svg 并运行 scripts/build_icon.py。
"""

from __future__ import annotations

import ctypes
import logging
from pathlib import Path
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets"
APP_USER_MODEL_ID = "litmgr.desktop"
log = logging.getLogger(__name__)


def configure_app_icon(app: QApplication) -> None:
    """设置全局图标，并为 Windows 任务栏提供稳定的应用标识。"""
    if sys.platform == "win32":
        try:
            set_id = ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID
            set_id.argtypes = [ctypes.c_wchar_p]
            set_id.restype = ctypes.c_long
            result = set_id(APP_USER_MODEL_ID)
            if result != 0:
                log.warning("设置任务栏应用标识失败：%s", result)
        except (AttributeError, OSError):
            log.exception("设置任务栏应用标识失败，继续使用窗口图标")
    icon = QIcon(str(ASSETS_DIR / "app-icon.ico"))
    if icon.isNull():
        icon = QIcon(str(ASSETS_DIR / "app-icon.svg"))
    if icon.isNull():
        log.warning("未找到有效应用图标")
        return
    app.setWindowIcon(icon)
