"""用本机 litmgr 的导入服务将已审阅的单论文文件夹导入当前配置的库。"""

import argparse
from collections import Counter
import json
from pathlib import Path
import sys


def package_files(folder: Path) -> list[Path]:
    """只接受技能 finalize 交付的单篇目录，避免导入多个目录或中间文件。"""
    stem = folder.name
    required = {stem + ".pdf", stem + "翻译.md", stem + "论文卡片.txt"}
    files = sorted(folder.iterdir())
    names = {path.name for path in files}
    if names not in (required, required | {stem + "补充材料.pdf"}):
        raise ValueError("目录内容与单篇成品不符")
    if not all(path.is_file() and path.stat().st_size for path in files):
        raise ValueError("成品文件缺失或为空")
    return files


def import_bundle(project: Path, folder: Path) -> dict:
    """遵守桌面程序的同库锁，在事务导入后核对库内文件内容。"""
    files = package_files(folder)
    if not (project / "litmgr/services/import_service.py").is_file():
        raise ValueError("请指定本机 litmgr 应用源码目录")
    sys.path.insert(0, str(project))
    from PySide6.QtCore import QLockFile
    from litmgr.core.config import AppConfig
    from litmgr.services.app_context import AppContext
    from litmgr.services.import_service import LabelDecision
    from litmgr.storage.library_fs import sha256_of

    configured = AppConfig.load().library_path
    if not configured or not Path(configured).is_absolute():
        raise ValueError("litmgr 尚未配置当前文献库的绝对路径")
    library = Path(configured).resolve()
    if library == project / "shared_library" or not (library / "db/litmgr.db").is_file():
        raise ValueError("当前配置未指向现有个人文献库")
    lock = QLockFile(str(library / ".litmgr.lock"))
    if not lock.tryLock(200):
        raise RuntimeError(f"无法取得文献库锁，请使用该库已打开的导入向导：{library}")
    try:
        ctx = AppContext(library)
        try:
            plan = ctx.imports.build_plan(files)
            if len(plan.items) != 1:
                raise ValueError("文件未配对为一篇论文")
            item = plan.items[0]
            if not item.parsed or not item.parsed.entries or item.group.fuzzy:
                raise ValueError("无法准确配对或解析卡片")
            paper_id = item.duplicate_of
            if paper_id is None:
                if item.warnings or item.action != "import":
                    raise ValueError(f"导入预览异常：{item.warnings}")
                decisions = {label.key: LabelDecision() for label in plan.unknown}
                result = ctx.imports.execute(plan, decisions)
                if result.errors or len(result.created) != 1:
                    raise RuntimeError(f"导入失败：{result.errors}")
                paper_id = result.created[0]
            expected = Counter(sha256_of(path) for path in files)
            stored = Counter(sha256_of(ctx.files.abs_path(file)) for file in ctx.files.list(paper_id))
            if expected - stored:
                raise ValueError(f"库内已有记录 #{paper_id}，但附件与成品不完全匹配，请核对该记录")
            return {"status": "duplicate" if item.duplicate_of else "imported",
                    "library": str(library), "paper_id": paper_id, "title": item.title,
                    "verified_files": len(files),
                    "pending_labels": [] if item.duplicate_of else [u.label for u in plan.unknown]}
        finally:
            ctx.close()
    finally:
        lock.unlock()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, type=Path, help="已安装的 litmgr 项目目录")
    parser.add_argument("folder", type=Path, help="finalize 返回的成品文件夹")
    args = parser.parse_args()
    try:
        print(json.dumps(import_bundle(args.project.resolve(), args.folder.resolve()), ensure_ascii=False))
    except (ImportError, OSError, ValueError, RuntimeError) as error:
        sys.exit(str(error))
