"""importers 导入解析层：把外部文件（论文卡片 txt、PDF、翻译 md 等）解析/配对成结构化数据。

只做“解析与配对”，不写数据库；入库由 services.import_service 完成。
只依赖标准库（不依赖 storage / ui），因此可以脱离界面单独测试。
"""
