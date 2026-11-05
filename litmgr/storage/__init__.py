"""storage 存储层：SQLite 数据库、迁移、各仓库（Repository）、文献库文件系统。

只依赖 core。仓库只做“数据读写”，不含业务规则（业务规则在 services）。
"""
