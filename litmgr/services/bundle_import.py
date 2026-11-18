"""核对并导入技能生成的单篇论文包。

【作用】在已持有目标文献库锁的进程内导入一篇论文，返回入库记录和实际待归类字段。
【依赖】AppContext 的导入、文件和待归类服务；沿用文献库复制文件的哈希算法。
【被谁调用】桌面程序的本机导入入口，以及软件关闭时技能使用的后台脚本。
【扩展点】技能的成品命名或校验要求变化时，在此维护两种入口共用的规则。
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from ..storage.library_fs import sha256_of
from .app_context import AppContext
from .import_service import LabelDecision


def _package_files(folder: Path) -> list[Path]:
    """检查目录仅含本篇的正文、译文、卡片和可选的补充材料。"""
    stem = folder.name
    required = {stem + ".pdf", stem + "翻译.md", stem + "论文卡片.txt"}
    files = sorted(folder.iterdir())
    names = {path.name for path in files}
    if names not in (required, required | {stem + "补充材料.pdf"}):
        raise ValueError("目录内容与单篇成品不符")
    if not all(path.is_file() and path.stat().st_size for path in files):
        raise ValueError("成品文件缺失或为空")
    return files


def import_bundle(ctx: AppContext, folder: Path) -> dict:
    """复用当前库的查重和事务导入，校验包内文件，只报告这篇论文的结果。"""
    files = _package_files(folder)
    plan = ctx.imports.build_plan(files)
    if len(plan.items) != 1:
        raise ValueError("文件未配对为一篇论文")
    item = plan.items[0]
    if not item.parsed or not item.parsed.entries or item.group.fuzzy:
        raise ValueError("无法准确配对或解析卡片")

    expected = Counter(sha256_of(path) for path in files)

    def verify_files(paper_id: int) -> None:
        # 逐个读取库内副本；一篇已有论文可以另外保存用户自行添加的附件。
        stored = Counter(sha256_of(ctx.files.abs_path(file)) for file in ctx.files.list(paper_id))
        if expected - stored:
            raise ValueError(f"论文 #{paper_id} 的库内附件与本次成品不完全匹配")

    paper_id = item.duplicate_of
    if paper_id is None:
        if item.warnings or item.action != "import":
            raise ValueError(f"导入预览异常：{item.warnings}")
        decisions = {label.key: LabelDecision() for label in plan.unknown}
        result = ctx.imports.execute(plan, decisions, verify_created=verify_files)
        if result.errors or len(result.created) != 1:
            raise RuntimeError(f"导入失败：{result.errors}")
        paper_id = result.created[0]
        status = "imported"
    else:
        verify_files(paper_id)
        status = "duplicate"

    return {"status": status, "library": str(ctx.library_path), "paper_id": paper_id,
            "title": item.title, "verified_files": len(files),
            "pending_labels": [entry.label for entry in ctx.pending.list(paper_id)]}
