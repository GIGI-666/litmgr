"""统一异常类型。

【作用】让各层抛出语义明确的异常，界面层据此给出友好的提示，而不是直接崩溃。
【被谁调用】storage / services 抛出；ui 捕获并弹窗提示。
【扩展点】新增业务错误时在此继承 LitmgrError 即可。
"""


class LitmgrError(Exception):
    """本系统所有业务异常的基类。"""


class NotFoundError(LitmgrError):
    """请求的论文/字段/文件等不存在。"""


class DuplicateError(LitmgrError):
    """名称或唯一标识重复（如字段名重复、论文重复）。"""


class ValidationError(LitmgrError):
    """用户输入不合法。"""
