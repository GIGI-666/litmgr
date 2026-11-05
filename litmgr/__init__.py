"""litmgr —— 个人文献管理系统（本地单机、离线）。

【作用】整个应用的顶层包，只放版本号等全局常量。
【分层】ui -> services -> storage -> core（依赖只能单向，禁止反向 import）。
    - core      领域模型、事件总线、注册表、配置、异常（不依赖其他层）
    - storage   SQLite 数据库、迁移、各仓库、文献库文件系统
    - importers 论文卡片解析、文件配对
    - services  业务服务（界面只调用这一层）
    - ui        全部界面（PySide6）
    - plugins   以后新增的功能模块
【被谁调用】`python -m litmgr` 启动（见 __main__.py）。
"""

__version__ = "0.1.0"
APP_NAME = "文献管理系统"
