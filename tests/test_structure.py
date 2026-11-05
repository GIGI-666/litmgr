"""结构调整后的测试：字段类型的条件判断、FileService / PendingService、
主窗口拆分后的各面板、窗口状态存入配置、显示列变化事件。
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication  # noqa: E402

from litmgr.core.config import AppConfig  # noqa: E402
from litmgr.core.events import Events  # noqa: E402
from litmgr.core.field_types import (OP_CONTAINS, OP_EMPTY, OP_EQUALS, OP_GT, OP_HAS,  # noqa: E402
                                     OP_LT, OP_NOT_EMPTY, get_type)
from litmgr.core.models import KIND_PDF, KIND_TRANSLATION  # noqa: E402
from litmgr.core.query import Condition, SearchQuery  # noqa: E402
from litmgr.services.app_context import AppContext  # noqa: E402
from litmgr.ui.window_manager import WindowManager  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def ctx(tmp_path):
    c = AppContext(tmp_path / "lib")
    yield c
    c.close()


# ---------- FieldType.matches ----------
def test_matches_text_ops():
    t = get_type("text")
    assert t.matches(OP_CONTAINS, "Hello World", None, "world")
    assert t.matches(OP_EQUALS, " hello  world ", None, "HELLO WORLD")
    assert t.matches(OP_EMPTY, "  ", None, "") and not t.matches(OP_EMPTY, "x", None, "")
    assert t.matches(OP_NOT_EMPTY, "x", None, "")


def test_matches_tags_has():
    t = get_type("tags")
    text, js = t.parse("OCR, 版面分析")
    assert t.matches(OP_HAS, text, js, "ocr")
    assert not t.matches(OP_HAS, text, js, "版面")        # 必须是完整标签
    assert not t.matches(OP_HAS, "", None, "ocr")


def test_matches_numeric_and_date_order():
    n = get_type("number")
    assert n.matches(OP_GT, "10", 10.0, "9") and not n.matches(OP_GT, "10", 10.0, "10")
    assert n.matches(OP_LT, "9", 9.0, "10")                # 数值比较，而不是字符串
    assert not n.matches(OP_GT, "", None, "1")             # 空值不参与比较
    d = get_type("date")
    assert d.matches(OP_GT, "2024-05-01", "2024-05-01", "2024-1-2")
    assert d.matches(OP_LT, "2023", "2023", "2024年")
    r = get_type("rating")
    assert r.matches(OP_GT, "4", 4, "3")


def test_search_uses_field_type_matching(ctx):
    year = ctx.fields.add("引用数", "number")
    title = ctx.fields.by_role("title")
    a = ctx.papers.create({title.id: "A", year.id: "100"})
    ctx.papers.create({title.id: "B", year.id: "9"})
    got = ctx.search.run(SearchQuery(conditions=[Condition(year.id, OP_GT, "50")]))
    assert [p.id for p in got] == [a]
    # SearchQuery 可序列化（保存的检索）并保持等价
    q = SearchQuery(text="x", conditions=[Condition(year.id, OP_LT, "5")])
    assert SearchQuery.from_dict(q.to_dict()) == q
    c = q.copy()
    c.conditions.append(Condition(1, OP_EMPTY))
    assert len(q.conditions) == 1                          # 深拷贝，互不影响


# ---------- FileService / PendingService ----------
def test_file_service_roundtrip(ctx, tmp_path):
    pid = ctx.papers.create()
    pdf = tmp_path / "a.pdf"
    pdf.write_bytes(b"%PDF-1.4 x")
    md = tmp_path / "a.md"
    md.write_text("这是一段独一无二的翻译正文关键词", encoding="utf-8")
    f1 = ctx.files.add(pid, KIND_PDF, pdf)
    ctx.files.add(pid, KIND_TRANSLATION, md)
    assert len(ctx.files.list(pid)) == 2
    assert ctx.files.abs_path(f1).exists()
    # 翻译正文能被全文搜索到
    assert [p.id for p in ctx.search.run(SearchQuery(text="独一无二的翻译"))] == [pid]
    ctx.files.set_subtype(f1.id, "appendix")
    assert ctx.files.list(pid, KIND_PDF)[0].subtype == "appendix"
    ctx.files.remove(f1.id)
    assert not ctx.files.abs_path(f1).exists()
    ctx.papers.delete(pid)                                  # 删除论文同时清掉索引与目录
    assert ctx.search.run(SearchQuery(text="独一无二的翻译")) == []
    assert not any(ctx.fs.papers_dir.iterdir())


def test_pending_service(ctx):
    notes = ctx.fields.add("补充", "longtext")
    pid = ctx.papers.create({notes.id: "旧内容"})
    pend_id = ctx.pending.add(pid, "杂项", "新内容")
    assert [p.content for p in ctx.pending.list(pid)] == ["新内容"]
    ctx.pending.assign(pend_id, notes.id)
    assert ctx.papers.get_field_text(pid, notes.id) == "旧内容\n新内容"
    assert ctx.pending.list(pid) == []
    pid2 = ctx.pending.add(pid, "杂项2", "x")
    ctx.pending.discard(pid2)
    assert ctx.pending.list() == []


# ---------- 显示列事件 ----------
def test_set_show_in_list_publishes_only_columns_event(ctx):
    f = ctx.fields.add("会议", "text")
    got = []
    ctx.events.subscribe(Events.LIST_COLUMNS_CHANGED, lambda **kw: got.append("cols"))
    ctx.events.subscribe(Events.FIELDS_CHANGED, lambda **kw: got.append("fields"))
    ctx.fields.set_show_in_list(f.id, True)
    assert got == ["cols"] and ctx.fields.get(f.id).show_in_list
    ctx.fields.set_show_in_list(f.id, True)               # 值未变不重复发布
    assert got == ["cols"]


# ---------- 主窗口拆分后的面板 ----------
def test_main_window_panels_and_saved_state(app, ctx, tmp_path, monkeypatch):
    monkeypatch.setenv("LITMGR_HOME", str(tmp_path / "home"))
    title = ctx.fields.by_role("title")
    col = ctx.organize.add_collection("甲组")
    a = ctx.papers.create({title.id: "论文A"})
    ctx.papers.create({title.id: "论文B"})
    ctx.organize.add_to_collection([a], col)
    cfg = AppConfig()
    wm = WindowManager(ctx)
    try:
        main = wm.open_main(cfg)
        # 导航：点分组 -> 列表只剩该分组的论文
        main.nav.setCurrentItem(main.nav._items[("collection", col)])
        main._refresh_timer.stop()
        assert main.nav_tuple == ("collection", col)
        assert main.table.paper_count() == 1
        # 预览：选中一篇后显示标题
        main.table.selectRow(0)
        assert "论文A" in main.preview.browser.toPlainText()
        assert main.preview.open_btn.isEnabled()
        # 清除 -> 回到全部
        main.clear_search()
        assert main.nav_tuple == ("all",) and main.table.paper_count() == 2
        # 窗口状态写入配置（而不是注册表），并可还原
        main.close()
        st = cfg.ui_state["main_window"]
        assert st["geometry"] and len(st["split"]) == 3
        assert (tmp_path / "home" / "config.json").exists()
        main2 = wm.open_main(cfg)
        assert main2.split.sizes()
    finally:
        wm.close_all()


# ---------- 性能优化的回归测试（功能必须保持不变） ----------
def test_search_loads_only_needed_fields_but_results_same(ctx):
    """检索只读取列表需要的字段值；用隐藏字段做过滤/排序时结果仍然正确。"""
    cites = ctx.fields.add("引用数", "number")                  # 不显示在列表里
    hidden = ctx.fields.add("备注", "longtext")
    title = ctx.fields.by_role("title")
    ids = [ctx.papers.create({title.id: f"T{i}", cites.id: str(i * 10), hidden.id: "x"})
           for i in range(5)]
    got = ctx.search.run(SearchQuery(conditions=[Condition(cites.id, OP_GT, "15")],
                                     sort_key=f"f:{cites.id}", sort_desc=False))
    assert [p.id for p in got] == ids[2:]                       # 条件字段、排序字段都读到了
    assert all(p.title for p in got)                            # 标题始终可用
    assert all(hidden.id not in p.values for p in got)          # 没用到的字段没有读
    assert ctx.papers.get(ids[0]).values[hidden.id].text == "x"  # get() 仍是完整数据


def test_titles_of_and_recent_titles(ctx):
    title = ctx.fields.by_role("title")
    a = ctx.papers.create({title.id: "甲"})
    b = ctx.papers.create({title.id: "乙"})
    assert ctx.papers.titles_of([a, b, 99999]) == {a: "甲", b: "乙"}
    assert ctx.papers.titles_of([]) == {}
    ctx.reading.record_open(a)
    ctx.reading.record_open(b)
    assert [(r.paper_id, r.title) for r in ctx.reading.recent()] == [(b, "乙"), (a, "甲")]


def test_markdown_page_cache_reuses_file(app, tmp_path):
    pytest.importorskip("PySide6.QtWebEngineWidgets")
    from litmgr.ui import md_viewer
    v = md_viewer.MarkdownViewer()
    v._dir = tmp_path
    v.load_text("# 你好 $x^2$")
    first = sorted(tmp_path.glob("page_*.html"))
    assert len(first) == 1
    mtime = first[0].stat().st_mtime_ns
    v.load_text("# 你好 $x^2$")                                  # 同内容：复用，不重写
    assert sorted(tmp_path.glob("page_*.html")) == first
    assert first[0].stat().st_mtime_ns >= mtime
    v.load_text("# 不同内容")
    assert len(list(tmp_path.glob("page_*.html"))) == 2
    for i in range(md_viewer._CACHE_KEEP + 5):                  # 缓存数量有上限
        (tmp_path / f"page_{i:04d}.html").write_text("x")
    md_viewer._prune_cache(tmp_path)
    assert len(list(tmp_path.glob("page_*.html"))) == md_viewer._CACHE_KEEP


def test_reader_loads_each_file_once(app, ctx, tmp_path, monkeypatch):
    """打开阅读窗口时 PDF / 翻译各只加载一次（以前会重复加载两遍）。"""
    pytest.importorskip("PySide6.QtWebEngineWidgets")
    from litmgr.ui.md_viewer import MarkdownViewer
    from litmgr.ui.pdf_viewer import PdfViewer
    pid = ctx.papers.create()
    pdf, md = tmp_path / "a.pdf", tmp_path / "a.md"
    pdf.write_bytes(b"%PDF-1.4 x")
    md.write_text("# t", encoding="utf-8")
    ctx.files.add(pid, KIND_PDF, pdf)
    ctx.files.add(pid, KIND_TRANSLATION, md)
    calls = {"pdf": 0, "md": 0}
    real_pdf, real_md = PdfViewer.load, MarkdownViewer.load_text
    monkeypatch.setattr(PdfViewer, "load",
                        lambda self, p: (calls.__setitem__("pdf", calls["pdf"] + 1), real_pdf(self, p))[1])
    monkeypatch.setattr(MarkdownViewer, "load_text",
                        lambda self, t: (calls.__setitem__("md", calls["md"] + 1), real_md(self, t))[1])
    wm = WindowManager(ctx)
    try:
        wm.open_reader(pid)
        assert calls == {"pdf": 1, "md": 1}
    finally:
        wm.close_all()
