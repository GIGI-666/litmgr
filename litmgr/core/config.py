"""应用配置（文献库位置等）。

【作用】保存“上次使用的文献库路径”等全局设置，存放在用户目录的 JSON 文件中。
【职责】
    - 读取/保存配置
    - 通过环境变量 LITMGR_HOME 可改变配置目录（测试时用）
【依赖】仅标准库。
【被谁调用】__main__ 启动流程；ui 的“切换文献库”功能。
【扩展点】新增全局设置项时在 AppConfig 增加字段即可。
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path


def config_dir() -> Path:
    """配置目录。优先 LITMGR_HOME，否则 %APPDATA%/litmgr（非 Windows 用 ~/.litmgr）。"""
    env = os.environ.get("LITMGR_HOME")
    if env:
        return Path(env)
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "litmgr"
    return Path.home() / ".litmgr"


@dataclass
class AppConfig:
    """全局配置。"""

    library_path: str = ""                       # 当前文献库文件夹
    recent_libraries: list[str] = field(default_factory=list)
    auto_backup: bool = True                     # 启动时自动备份
    backup_keep: int = 10                        # 最多保留几份自动备份
    ui_state: dict = field(default_factory=dict)  # 界面状态（窗口位置/分栏等），按窗口名分键存放

    @classmethod
    def load(cls) -> "AppConfig":
        path = config_dir() / "config.json"
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                known = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
                return cls(**known)
            except (OSError, ValueError):
                pass  # 配置损坏时回退默认值，不阻止启动
        return cls()

    def save(self) -> None:
        d = config_dir()
        d.mkdir(parents=True, exist_ok=True)
        (d / "config.json").write_text(
            json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def remember_library(self, path: str) -> None:
        """记录当前文献库并维护最近使用列表。"""
        self.library_path = path
        if path in self.recent_libraries:
            self.recent_libraries.remove(path)
        self.recent_libraries.insert(0, path)
        del self.recent_libraries[8:]
