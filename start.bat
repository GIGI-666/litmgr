@echo off
rem 双击启动文献管理系统（使用本文件夹下的 .venv 虚拟环境）
cd /d "%~dp0"
if exist ".venv\Scripts\pythonw.exe" (
    start "" ".venv\Scripts\pythonw.exe" -m litmgr
) else (
    echo 未找到 .venv 虚拟环境，请先运行：python -m venv .venv ^&^& .venv\Scripts\pip install -r requirements.txt
    pause
)
