"""程序入口：`python -m litmgr [--library 文献库文件夹]`。

【作用】启动应用：创建 QApplication，确定文献库位置（命令行 > 上次使用 > 首次启动时让你选择），
    装配 AppContext，自动备份，打开主窗口，进入事件循环；退出时关闭数据库。
【依赖】core.config；services.app_context；ui.window_manager / ui.utils。
【扩展点】插件加载：在 main() 里 ctx 创建之后、主窗口打开之前调用插件的 register(ctx, windows)。
"""

from __future__ import annotations

import argparse
import logging
import sys
import traceback
from pathlib import Path

from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from . import APP_NAME
from .core.config import AppConfig, config_dir
from .services.app_context import AppContext
from .ui.utils import apply_app_style
from .ui.window_manager import WindowManager


def _setup_logging() -> None:
    d = config_dir()
    d.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.FileHandler(d / "litmgr.log", encoding="utf-8"),
                  logging.StreamHandler(sys.stderr)])


def _choose_library(config: AppConfig, cli_path: str | None) -> Path | None:
    """确定要打开的文献库：命令行 > 配置里上次使用的 > 弹窗选择。"""
    if cli_path:
        return Path(cli_path)
    if config.library_path and Path(config.library_path).parent.exists():
        return Path(config.library_path)
    QMessageBox.information(
        None, APP_NAME,
        "欢迎使用！请选择一个文件夹作为“文献库”。\n"
        "论文的 PDF、翻译、数据库都会保存在这个文件夹里，\n"
        "以后复制整个文件夹就能备份或迁移。\n\n（可以选一个新建的空文件夹）")
    d = QFileDialog.getExistingDirectory(None, "选择文献库文件夹", str(Path.home() / "Documents"))
    return Path(d) if d else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="litmgr", description=APP_NAME)
    parser.add_argument("--library", help="文献库文件夹路径（不指定则用上次的）")
    args = parser.parse_args(argv)

    _setup_logging()
    app = QApplication(sys.argv[:1])
    app.setApplicationName(APP_NAME)
    apply_app_style(app)

    def excepthook(exc_type, exc, tb) -> None:
        logging.error("未捕获异常\n%s", "".join(traceback.format_exception(exc_type, exc, tb)))
        QMessageBox.critical(None, APP_NAME, f"发生未预期的错误：\n{exc}\n\n详情见日志：{config_dir() / 'litmgr.log'}")

    sys.excepthook = excepthook

    config = AppConfig.load()
    library = _choose_library(config, args.library)
    if library is None:
        return 0
    library.mkdir(parents=True, exist_ok=True)
    config.remember_library(str(library))
    config.save()

    ctx = AppContext(library)
    try:
        if config.auto_backup:
            ctx.backup.auto_backup(keep=config.backup_keep)
    except Exception:  # noqa: BLE001 - 备份失败不应阻止使用
        logging.exception("自动备份失败")

    windows = WindowManager(ctx)
    windows.open_main(config)
    code = app.exec()
    ctx.close()
    return code


if __name__ == "__main__":
    raise SystemExit(main())
