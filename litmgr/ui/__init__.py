"""ui 界面层（PySide6）。

只通过 AppContext 暴露的服务访问业务功能，不直接访问数据库；
窗口之间通过 core.events 事件总线保持同步，通过 WindowManager 打开/管理多窗口。
"""
