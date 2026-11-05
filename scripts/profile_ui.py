"""性能剖析脚本：在文献库的副本上测量常用操作的耗时（不会改动原库）。

用法：.venv\\Scripts\\python.exe scripts/profile_ui.py <文献库副本路径> [--cprofile] [--prewarm]
"""

import cProfile
import os
import pstats
import sys
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--no-sandbox --disable-gpu")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtCore import QEventLoop, QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from litmgr.services.app_context import AppContext  # noqa: E402
from litmgr.ui.utils import apply_app_style  # noqa: E402
from litmgr.ui.window_manager import WindowManager  # noqa: E402

PROFILE = "--cprofile" in sys.argv


def pump(ms=50):
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def timed(label, fn, settle=0):
    t = time.perf_counter()
    if PROFILE:
        pr = cProfile.Profile()
        pr.enable()
        fn()
        pr.disable()
    else:
        fn()
    dt = (time.perf_counter() - t) * 1000
    if settle:
        pump(settle)
    print(f"{dt:8.1f} ms  {label}")
    if PROFILE and dt > 30:
        pstats.Stats(pr).sort_stats("cumulative").print_stats(12)


def main():
    lib = Path(sys.argv[1])
    t0 = time.perf_counter()
    app = QApplication([])
    apply_app_style(app)
    print(f"{(time.perf_counter() - t0) * 1000:8.1f} ms  QApplication+样式")
    ctx = [None]
    timed("AppContext", lambda: ctx.__setitem__(0, AppContext(lib)))
    ctx = ctx[0]
    wm = WindowManager(ctx)
    win = [None]
    timed("打开主窗口", lambda: win.__setitem__(0, wm.open_main(None)), settle=300)
    main_win = win[0]
    timed("show 主窗口", main_win.show, settle=300)
    timed("refresh()", main_win.refresh)
    timed("search.run()", lambda: ctx.search.run())
    for r in (0, 1, 2):
        timed(f"选中第 {r} 行", lambda r=r: main_win.table.selectRow(r), settle=50)
    timed("搜索“检测”", lambda: main_win.search_edit.setText("检测"), settle=600)
    timed("清除搜索", main_win.clear_search, settle=100)
    pid = ctx.papers.list_titles()[0].id
    d = [None]
    timed("打开详情窗口", lambda: d.__setitem__(0, wm.open_detail(pid)), settle=300)
    timed("show 详情", d[0].show, settle=300)
    timed("详情改状态 -> 事件刷新", lambda: ctx.papers.set_rating(pid, 3), settle=300)
    if "--prewarm" in sys.argv:      # 模拟程序启动后的空闲预热
        from litmgr.ui import reader_window  # noqa: F401
        from litmgr.ui.md_viewer import prewarm
        timed("预热 WebEngine", prewarm, settle=1500)
    r = [None]
    timed("打开阅读窗口", lambda: r.__setitem__(0, wm.open_reader(pid)), settle=100)
    timed("show 阅读窗口", r[0].show, settle=1500)
    timed("关闭阅读窗口", r[0].close, settle=100)
    timed("打开对比窗口", lambda: wm.open_compare([p.id for p in ctx.papers.list_titles()[:4]]),
          settle=300)
    wm.close_all()
    from litmgr.ui.md_viewer import release_prewarm
    release_prewarm()
    ctx.close()


if __name__ == "__main__":
    main()
