"""在项目文件夹中创建带应用图标的 Windows 启动快捷方式。

【作用】让用户双击“文献管理系统”快捷方式启动，启动入口也显示专属图标。
【职责】使用当前项目的虚拟环境、工作目录和 ICO，保存后重新读取并核对设置。
【依赖】标准库与 Windows 自带 PowerShell/WScript.Shell；不操作文献库或系统设置。
【被谁调用】维护者或用户在安装依赖后手动运行，不在应用启动时重复创建。
【扩展点】快捷方式的名称、描述和启动参数集中在 create_shortcut 中维护。
"""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import subprocess
import sys


def ps_quote(value: str | Path) -> str:
    """转成 PowerShell 单引号字面量，路径中的单引号不得变成命令。"""
    return "'" + str(value).replace("'", "''") + "'"


def create_shortcut(root: Path) -> Path:
    """创建/更新本项目的启动快捷方式，验证目标、工作目录和图标后返回路径。"""
    if sys.platform != "win32":
        raise OSError("此快捷方式仅用于 Windows，其他系统请用 python -m litmgr")
    root = root.resolve()
    pythonw = root / ".venv/Scripts/pythonw.exe"
    icon = root / "litmgr/assets/app-icon.ico"
    link = root / "文献管理系统.lnk"
    if not pythonw.is_file() or not icon.is_file():
        raise FileNotFoundError("请先安装项目虚拟环境，并确认应用图标已生成")
    # 编码传递脚本，既兼容 Windows PowerShell 5 的中文，也避免路径参与 shell 展开。
    command = f"""
$ErrorActionPreference = 'Stop'
$shortcutShell = New-Object -ComObject WScript.Shell
$shortcut = $shortcutShell.CreateShortcut({ps_quote(link)})
$shortcut.TargetPath = {ps_quote(pythonw)}
$shortcut.Arguments = '-m litmgr'
$shortcut.WorkingDirectory = {ps_quote(root)}
$shortcut.IconLocation = {ps_quote(str(icon) + ',0')}
$shortcut.Description = '个人文献管理系统 litmgr'
$shortcut.Save()
$check = $shortcutShell.CreateShortcut({ps_quote(link)})
$result = @{{ target = $check.TargetPath; arguments = $check.Arguments; work = $check.WorkingDirectory; icon = $check.IconLocation }}
[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes(($result | ConvertTo-Json -Compress)))
"""
    encoded = base64.b64encode(command.encode("utf-16-le")).decode("ascii")
    powershell = Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    result = subprocess.run([str(powershell), "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
                            capture_output=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
    settings = json.loads(base64.b64decode(result.stdout.strip()).decode("utf-8"))
    if (not link.is_file() or Path(settings["target"]) != pythonw or settings["arguments"] != "-m litmgr"
            or Path(settings["work"]) != root or settings["icon"].rsplit(",", 1)[0] != str(icon)):
        raise ValueError("快捷方式设置校验失败")
    return link


def main() -> None:
    """为当前项目生成图标快捷方式。"""
    root = Path(__file__).resolve().parents[1]
    link = create_shortcut(root)
    print(json.dumps({"shortcut": str(link)}, ensure_ascii=True))


if __name__ == "__main__":
    main()
