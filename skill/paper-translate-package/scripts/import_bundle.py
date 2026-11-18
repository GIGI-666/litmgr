"""将已审阅的单篇论文包在后台导入 litmgr 当前个人库。

【作用】读取本机配置，按文献库锁的归属选择直接导入或把请求交给已打开的软件。
【依赖】litmgr 项目的 Python 环境、Qt 库锁、本机通信及单篇导入服务。
【被谁调用】论文翻译技能在成品校验后运行；命令行输出 JSON 结果或具体错误。
【扩展点】成品规则和查重逻辑由应用的 services.bundle_import 统一维护。
"""

import argparse
import json
from pathlib import Path
import sys


def import_bundle(project: Path, folder: Path) -> dict:
    """由持锁进程执行单篇导入；整个过程只交换命令和回执。"""
    project, folder = project.resolve(), folder.resolve()
    if not (project / "litmgr/local_import.py").is_file():
        raise ValueError("请指定支持后台导入的新版 litmgr 项目目录")
    sys.path.insert(0, str(project))
    from PySide6.QtCore import QLockFile
    from litmgr.core.config import AppConfig
    from litmgr.local_import import ImportServerUnavailable, import_from_running
    from litmgr.services.app_context import AppContext
    from litmgr.services.bundle_import import import_bundle as import_into_context

    configured = AppConfig.load().library_path
    if not configured or not Path(configured).is_absolute():
        raise ValueError("litmgr 尚未配置当前文献库的绝对路径")
    library = Path(configured).resolve()
    if library == (project / "shared_library").resolve() or not (library / "db/litmgr.db").is_file():
        raise ValueError("当前配置未指向现有个人文献库")
    lock = QLockFile(str(library / ".litmgr.lock"))
    if not lock.tryLock(200):
        if lock.error() != QLockFile.LockFailedError:
            raise RuntimeError(f"无法取得文献库写入权限：{library}")
        try:
            return import_from_running(library, folder)
        except ImportServerUnavailable:
            # 桌面退出或另一后台任务完成后，改由本进程持锁。已发送的请求不会走到这里。
            if not lock.tryLock(200):
                raise
    try:
        ctx = AppContext(library)
        try:
            return import_into_context(ctx, folder)
        finally:
            ctx.close()
    finally:
        lock.unlock()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--project", required=True, type=Path, help="本机 litmgr 项目目录")
    parser.add_argument("folder", type=Path, help="finalize 返回的成品文件夹")
    args = parser.parse_args()
    try:
        print(json.dumps(import_bundle(args.project, args.folder), ensure_ascii=False))
    except (ImportError, OSError, ValueError, RuntimeError) as error:
        sys.exit(str(error))
