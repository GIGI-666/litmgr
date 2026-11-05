"""界面冒烟测试（离屏）：导入真实示例数据，依次创建各窗口并截图到 scripts/_shots/。

用法：.venv\\Scripts\\python.exe scripts/ui_smoke.py
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--no-sandbox --disable-gpu")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtCore import QCoreApplication, Qt, QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from litmgr.services.app_context import AppContext  # noqa: E402
from litmgr.services.import_service import ACT_NEW, LabelDecision  # noqa: E402
from litmgr.ui.utils import apply_app_style  # noqa: E402
from litmgr.ui.window_manager import WindowManager  # noqa: E402

REAL = Path(r"D:\2file\研究生2026.9.7\零散论文")
SHOTS = Path(__file__).parent / "_shots"


def pump(ms=600):
    loop_end = QTimer()
    loop_end.setSingleShot(True)
    from PySide6.QtCore import QEventLoop
    loop = QEventLoop()
    loop_end.timeout.connect(loop.quit)
    loop_end.start(ms)
    loop.exec()


def shot(win, name):
    win.show()
    pump(500)
    SHOTS.mkdir(exist_ok=True)
    win.grab().save(str(SHOTS / f"{name}.png"))
    print("saved", name)


def main():
    tmp = Path(tempfile.mkdtemp(prefix="litmgr_ui_"))
    app = QApplication([])
    apply_app_style(app)
    ctx = AppContext(tmp / "lib")
    wm = WindowManager(ctx)

    plan = ctx.imports.build_plan([REAL / "论文卡片", REAL / "零散论文翻译"] + list(REAL.glob("*.pdf")))
    ctx.imports.execute(plan, {u.key: LabelDecision(ACT_NEW) for u in plan.unknown
                               if u.label == "当前发表状态"})
    main_win = wm.open_main(None)
    main_win.resize(1500, 800)
    pump(300)
    shot(main_win, "01_main")

    papers = ctx.papers.list_all()
    rt = next(p for p in papers if "RT-DocLayout" in p.title)
    main_win.table.selectRow(0)
    pump(200)
    shot(main_win, "02_main_selected")

    # 搜索
    main_win.search_edit.setText("阅读顺序")
    pump(600)
    shot(main_win, "03_main_search")

    d = wm.open_detail(rt.id)
    d.resize(900, 900)
    shot(d, "04_detail")
    d.tabs.setCurrentIndex(1)
    shot(d, "05_detail_files")

    c = wm.open_compare([p.id for p in papers if p.title][:3])
    shot(c, "06_compare")

    r = wm.open_reader(rt.id)
    pump(2500)
    shot(r, "07_reader")

    from litmgr.ui.field_manager_dialog import FieldManagerDialog
    fm = FieldManagerDialog(main_win, ctx)
    shot(fm, "08_fields")

    from litmgr.ui.import_wizard import ImportWizard
    w = ImportWizard(main_win, ctx)
    w._add_path(REAL / "论文卡片")
    w._next()
    shot(w, "09_wizard_preview")
    w._next()
    shot(w, "10_wizard_labels")

    print("OK")
    wm.close_all()
    main_win.close()
    ctx.close()
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
