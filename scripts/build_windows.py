"""生成包含 Python、QtPdf、QtWebEngine 和离线公式资源的 Windows 文件夹版。"""

from __future__ import annotations

import argparse
from datetime import datetime
import os
from pathlib import Path
import subprocess
import sys


def main() -> None:
    """在新目录构建可执行程序，避免覆盖已有发布包。"""
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=root / "dist" / datetime.now().strftime("%Y%m%d-%H%M%S"))
    args = parser.parse_args()
    if sys.platform != "win32":
        parser.error("请在 Windows 64 位 Python 环境中打包。")
    output = args.output.resolve()
    if output.exists():
        parser.error(f"输出目录已存在，请使用新目录：{output}")
    output.mkdir(parents=True)
    env = dict(os.environ, PYTHONUTF8="1")
    subprocess.run([
        sys.executable, "-m", "PyInstaller", "--onedir", "--windowed", "--noupx",
        "--name", "litmgr", "--paths", str(root),
        "--icon", str(root / "litmgr/assets/app-icon.ico"),
        "--add-data", f"{root / 'litmgr/assets'};litmgr/assets",
        "--add-data", f"{root / 'litmgr/storage/migrations'};litmgr/storage/migrations",
        "--collect-submodules", "litmgr",
        "--distpath", str(output), "--workpath", str(output / "build"),
        "--specpath", str(output / "build"), str(root / "scripts/windows_entry.py"),
    ], cwd=root, env=env, check=True)
    (output / "litmgr" / "使用说明.txt").write_text(
        "双击 litmgr.exe 启动，无需安装 Python。\n"
        "请保留整个文件夹及 _internal，不能只复制 exe。\n"
        "首次启动请选择文献库文件夹；已有文献库直接选择原文件夹。\n"
        "论文和数据库保存在所选文献库中，不随软件打包。\n"
        "配置与日志默认保存在 %APPDATA%/litmgr。\n"
        "升级时解压到新位置，继续选择原文献库；请先备份文献库。\n",
        encoding="utf-8-sig",
    )
    print(f"打包完成：{output / 'litmgr' / 'litmgr.exe'}")


if __name__ == "__main__":
    main()
