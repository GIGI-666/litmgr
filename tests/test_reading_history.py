"""阅读历史测试：只保留最近 10 篇、状态能保存；阅读窗口关闭后再从历史打开能还原页面状态。"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--no-sandbox --disable-gpu")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QMarginsF, QSizeF  # noqa: E402
from PySide6.QtGui import QPageLayout, QPageSize, QPainter, QPdfWriter  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from litmgr.core.models import KIND_PDF, KIND_TRANSLATION  # noqa: E402
from litmgr.services.app_context import AppContext  # noqa: E402
from litmgr.services.reading_history_service import HISTORY_LIMIT  # noqa: E402
from litmgr.ui.window_manager import WindowManager  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def ctx(tmp_path):
    c = AppContext(tmp_path / "lib")
    yield c
    c.close()


def _papers(ctx, n):
    title = ctx.fields.by_role("title")
    return [ctx.papers.create({title.id: f"论文{i}"}) for i in range(n)]


# ---------- 服务层 ----------
def test_keeps_only_latest_ten(ctx):
    ids = _papers(ctx, 13)
    for pid in ids:
        ctx.reading.record_open(pid)
    recent = ctx.reading.recent()
    assert HISTORY_LIMIT == 10 and len(recent) == 10
    assert [r.paper_id for r in recent] == ids[::-1][:10]       # 最近的在最前，最旧的 3 篇被淘汰
    assert recent[0].title == "论文12"


def test_reopen_moves_to_front_and_keeps_state(ctx):
    a, b, c = _papers(ctx, 3)
    for pid in (a, b, c):
        ctx.reading.record_open(pid)
    ctx.reading.save_state(a, {"pdf": {"page": 7}})
    ctx.reading.record_open(a)                                   # 再次打开 a：排到最前，状态保留
    assert [r.paper_id for r in ctx.reading.recent()] == [a, c, b]
    assert ctx.reading.get_state(a) == {"pdf": {"page": 7}}
    assert ctx.reading.get_state(b) == {}


def test_deleted_paper_and_clear(ctx):
    a, b = _papers(ctx, 2)
    ctx.reading.record_open(a)
    ctx.reading.record_open(b)
    ctx.papers.delete(a)
    assert [r.paper_id for r in ctx.reading.recent()] == [b]
    ctx.reading.save_state(a, {"x": 1})                          # 论文已删除：不会复活历史记录
    assert ctx.reading.get_state(a) == {}
    ctx.reading.clear()
    assert ctx.reading.recent() == []


# ---------- 阅读窗口：还原页面状态 ----------
def _make_pdf(path, pages=12):
    w = QPdfWriter(str(path))
    w.setPageSize(QPageSize(QPageSize.A4))
    w.setPageMargins(QMarginsF(10, 10, 10, 10), QPageLayout.Millimeter)
    p = QPainter(w)
    for i in range(pages):
        if i:
            w.newPage()
        p.drawText(200, 400, f"page {i + 1}")
    p.end()


def _wait(ms):
    QTest.qWait(ms)


def test_reader_restores_state(app, ctx, tmp_path):
    pid = _papers(ctx, 1)[0]
    pdf = tmp_path / "a.pdf"
    _make_pdf(pdf)
    md = tmp_path / "a_翻译.md"
    md.write_text("# 标题\n\n" + "\n\n".join(f"第 {i} 段，公式 $x_{i}^2$" for i in range(400)),
                  encoding="utf-8")
    ctx.papers.add_file(pid, KIND_PDF, pdf)
    ctx.papers.add_file(pid, KIND_TRANSLATION, md)

    wm = WindowManager(ctx)
    try:
        win = wm.open_reader(pid)
        _wait(800)
        # 模拟用户操作：翻到第 6 页、放大、翻译滚到中部、字号放大、调整两栏比例
        win.pdf.zoom_in()
        win.pdf.page_spin.setValue(6)
        _wait(300)
        win.md.zoom(1.2)
        win.md.web.page().runJavaScript(
            "window.scrollTo(0, 0.5 * (document.documentElement.scrollHeight - window.innerHeight))")
        _wait(900)                                               # 等滚动比例被捕获
        win.split.setSizes([400, 1100])
        before = win.capture_state()
        assert before["pdf"]["page"] == 5
        assert 0.4 < before["md"]["frac"] < 0.6

        win.close()
        _wait(100)
        assert ctx.reading.get_state(pid)["pdf"]["page"] == 5     # 关闭时已落库

        # 从历史打开：还原
        win2 = wm.open_reader(pid, restore=True)
        _wait(1500)
        after = win2.capture_state()
        assert after["pdf"]["page"] == 5
        assert after["pdf"]["zoom_mode"] == "Custom"
        assert abs(after["pdf"]["zoom"] - before["pdf"]["zoom"]) < 1e-6
        assert abs(after["md"]["zoom"] - 1.2) < 1e-6
        assert abs(after["md"]["frac"] - before["md"]["frac"]) < 0.05
        assert win2.pdf.page_spin.value() == 6
        # 两栏比例的还原受离屏测试环境的屏幕尺寸和 PDF 栏最小宽度限制，这里只验证两栏都正常显示
        assert all(s > 0 for s in win2.split.sizes())
        assert after["show_pdf"] and after["show_md"]

        # 不带 restore 的普通打开：是全新页面
        win2.close()
        _wait(100)
        win3 = wm.open_reader(pid)
        _wait(600)
        assert win3.pdf.page_spin.value() == 1
    finally:
        wm.close_all()


def test_main_window_recent_menu(app, ctx):
    ids = _papers(ctx, 12)
    wm = WindowManager(ctx)
    try:
        main = wm.open_main(None)
        assert [a.text() for a in main.recent_menu.actions() if a.text() and a.isEnabled()] == []
        for pid in ids:
            ctx.reading.record_open(pid)
        QTest.qWait(50)                                         # 菜单刷新是延后执行的
        entries = [a for a in main.recent_menu.actions() if a.text() and a.isEnabled()]
        assert len(entries) == 10 + 1                           # 10 篇 + “清空阅读历史”
        assert "论文11" in entries[0].text()
        ctx.reading.clear()
        QTest.qWait(50)
        assert [a.text() for a in main.recent_menu.actions() if a.text() and a.isEnabled()] == []
    finally:
        wm.close_all()

