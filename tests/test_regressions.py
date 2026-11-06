"""回归测试：针对代码审查中发现的真实 bug，防止以后再次出现。

覆盖：PDF 内搜索、从旧版本备份恢复、导入中途失败回滚、待归类内容的 HTML 转义、
    笔记切换自动保存、迁移的原子性与升级前备份、批量操作的事务性能。
"""

import os
import sqlite3
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--no-sandbox --disable-gpu")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QMarginsF  # noqa: E402
from PySide6.QtGui import QPageLayout, QPageSize, QPainter, QPdfWriter  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QLabel  # noqa: E402

from litmgr.services.app_context import AppContext  # noqa: E402
from litmgr.storage import database as database_mod  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def ctx(tmp_path):
    c = AppContext(tmp_path / "lib")
    yield c
    c.close()


def _title(ctx):
    return ctx.fields.by_role("title")


def _make_pdf(path, pages=5):
    w = QPdfWriter(str(path))
    w.setPageSize(QPageSize(QPageSize.A4))
    w.setPageMargins(QMarginsF(10, 10, 10, 10), QPageLayout.Millimeter)
    p = QPainter(w)
    for i in range(pages):
        if i:
            w.newPage()
        p.drawText(200, 400, f"hello page {i + 1} zebra" if i == 2 else f"hello page {i + 1}")
    p.end()


# ---------- bug 1：PDF 内搜索 ----------
def test_pdf_search_works(app, tmp_path):
    from litmgr.ui.pdf_viewer import PdfViewer
    pdf = tmp_path / "s.pdf"
    _make_pdf(pdf)
    v = PdfViewer()
    assert v.load(str(pdf))
    v.search_edit.setText("zebra")
    v._search()                       # 修复前这里（及其异步回调）会抛 TypeError
    for _ in range(40):
        QTest.qWait(50)
        if v._hit_count() > 0:
            break
    assert v._hit_count() >= 1
    QTest.qWait(100)
    assert v.search_info.text().startswith("1/")
    v._goto_hit(+1)                   # 翻到下一个结果也不应报错


# ---------- bug 2：从旧版本备份恢复 ----------
def test_restore_old_schema_backup(ctx, tmp_path):
    ctx.papers.create({_title(ctx).id: "A"})
    old = tmp_path / "old.db"
    src, dst = sqlite3.connect(ctx.fs.db_path), sqlite3.connect(old)
    src.backup(dst)
    dst.execute("DROP TABLE reading_history")
    dst.execute("PRAGMA user_version=1")
    dst.commit()
    dst.close()
    src.close()
    ctx.backup.restore(old)
    assert ctx.db.query_one("PRAGMA user_version")[0] >= 2     # 已补跑迁移
    assert ctx.reading.recent() == []                          # 阅读历史表可用
    assert ctx.db.query_one("PRAGMA foreign_keys")[0] == 1


# ---------- bug 3：导入中途失败要回滚 ----------
def test_import_failure_leaves_no_half_paper(ctx, tmp_path, monkeypatch):
    src = tmp_path / "src"
    src.mkdir()
    (src / "测试论文2406论文卡片.txt").write_text("中文标题：测试论文\n", encoding="utf-8")
    (src / "测试论文2406.pdf").write_bytes(b"%PDF-1.4 fake")
    plan = ctx.imports.build_plan([src])
    assert len(plan.items) == 1

    real_add_file = ctx.files.add

    def flaky(pid, kind, path, **kw):
        if kind == "pdf":
            raise OSError("磁盘已满（模拟）")
        return real_add_file(pid, kind, path, **kw)

    monkeypatch.setattr(ctx.files, "add", flaky)
    res = ctx.imports.execute(plan, {})
    assert len(res.errors) == 1 and res.created == []
    assert ctx.papers.count() == 0                              # 数据库里没有半成品
    assert not any((ctx.fs.papers_dir).iterdir())               # 已复制的文件也被清理

    monkeypatch.undo()
    res = ctx.imports.execute(ctx.imports.build_plan([src]), {})   # 修复后能正常导入
    assert len(res.created) == 1 and ctx.papers.count() == 1


# ---------- bug 4：待归类内容要转义 ----------
def test_pending_content_is_escaped(app, ctx):
    from litmgr.ui.field_form import PaperFieldForm
    pid = ctx.papers.create({_title(ctx).id: "P"})
    ctx.pending.add(pid, "<b>标签</b>", "x < y & <script>")
    form = PaperFieldForm(ctx, pid)
    texts = [lb.text() for lb in form.pending_box.findChildren(QLabel)]
    assert any("&lt;script&gt;" in t and "&lt;b&gt;" in t for t in texts)


# ---------- bug 5：笔记切换自动保存 ----------
def test_note_autosave_on_switch(app, ctx):
    from litmgr.ui.note_panel import NotePanel
    pid = ctx.papers.create({_title(ctx).id: "P"})
    n1 = ctx.notes.add(pid, "第一条")
    n2 = ctx.notes.add(pid, "第二条")
    panel = NotePanel(ctx, pid)
    ctx.events.subscribe("notes_changed", lambda **kw: panel.refresh())   # 模拟详情窗口的刷新
    items = {panel.list.item(i).data(0x100)[0]: panel.list.item(i) for i in range(panel.list.count())}
    panel.list.setCurrentItem(items[n1])
    assert panel.edit.toPlainText() == "第一条"
    panel.edit.setPlainText("第一条（改过但没点保存）")
    panel.list.setCurrentItem(items[n2])
    QTest.qWait(50)
    contents = {n.id: n.content for n in ctx.notes.list(pid)}
    assert contents[n1] == "第一条（改过但没点保存）"
    assert panel.edit.toPlainText() == "第二条"
    # 关闭前的 flush
    panel.edit.setPlainText("第二条-再改")
    panel.flush()
    assert {n.id: n.content for n in ctx.notes.list(pid)}[n2] == "第二条-再改"


# ---------- 迁移：原子 + 升级前备份 ----------
def test_migration_is_atomic_and_snapshots(tmp_path, monkeypatch):
    mig = tmp_path / "mig"
    mig.mkdir()
    (mig / "0001_a.sql").write_text("CREATE TABLE a(x INTEGER);", encoding="utf-8")
    monkeypatch.setattr(database_mod, "MIGRATIONS_DIR", mig)
    dbfile, bdir = tmp_path / "t.db", tmp_path / "bk"
    database_mod.Database(dbfile, backup_dir=bdir).close()
    assert not bdir.exists()                       # 全新库不需要备份

    (mig / "0002_bad.sql").write_text(
        "CREATE TABLE b(x INTEGER);\nINSERT INTO no_such_table VALUES (1);", encoding="utf-8")
    with pytest.raises(sqlite3.Error):
        database_mod.Database(dbfile, backup_dir=bdir)
    con = sqlite3.connect(dbfile)
    assert con.execute("PRAGMA user_version").fetchone()[0] == 1
    assert con.execute("SELECT name FROM sqlite_master WHERE name='b'").fetchone() is None
    con.close()
    assert len(list(bdir.glob("*premigrate_v1*.db"))) == 1     # 升级前留了快照


# ---------- 批量操作用事务：不再逐条提交 ----------
def test_reindex_all_is_fast(ctx):
    title = _title(ctx)
    fields = ctx.fields.list()
    with ctx.db.transaction():
        for i in range(150):
            ctx.papers.create({f.id: f"内容{i} 版面分析" for f in fields[:10]}, publish=False)
    t = time.time()
    ctx.papers.reindex_all()
    assert time.time() - t < 5          # 修复前（每条语句一次提交）这个规模要慢得多
    assert title is not None


# ---------- 第五轮：复查中确认的问题 ----------
def test_undo_last_skips_deleted_field(ctx):
    """永久删除字段后，其历史记录不应让“撤销上一次”卡死。"""
    t = _title(ctx)
    f = ctx.fields.add("临时字段", "text")
    p = ctx.papers.create({t.id: "T"})
    ctx.papers.set_field(p, t.id, "T2")
    ctx.papers.set_field(p, f.id, "x")
    ctx.fields.archive(f.id)
    ctx.fields.delete_permanently(f.id)
    e = ctx.history.undo_last()
    assert e is not None and e.field_id == t.id
    assert ctx.papers.get(p).title == "T"


def test_status_sort_follows_progress(ctx):
    from litmgr.core.query import SearchQuery
    t = _title(ctx)
    for i, st in enumerate(["deep", "unread", "read", "reading"]):
        ctx.papers.set_status(ctx.papers.create({t.id: f"S{i}"}), st)
    res = ctx.search.run(SearchQuery(sort_key="status", sort_desc=False))
    assert [p.read_status for p in res] == ["unread", "reading", "read", "deep"]


def test_collect_files_dedupes_folder_and_file(tmp_path):
    from litmgr.importers.file_pairing import pair_files
    d = tmp_path / "src"
    d.mkdir()
    (d / "Foo Bar2406.pdf").write_bytes(b"%PDF-1")
    groups = pair_files([d, d / "Foo Bar2406.pdf"])
    assert len(groups) == 1 and len(groups[0].pdfs) == 1


def test_detail_window_keeps_typing_on_library_changed(app, ctx):
    from litmgr.core.events import Events
    from litmgr.ui.window_manager import WindowManager
    f = next(x for x in ctx.fields.list() if x.type == "longtext")
    p = ctx.papers.create({_title(ctx).id: "T"})
    win = WindowManager(ctx).open_detail(p)
    win.activateWindow()
    ed = win.form.editors[f.id]
    ed.edit.setFocus()
    app.processEvents()
    QTest.keyClicks(ed.edit, "typing")
    ctx.events.publish(Events.LIBRARY_CHANGED)
    assert win.form.editors[f.id].text() == "typing"
    win.close()


def test_auto_backup_prune_keeps_labeled(ctx):
    t = _title(ctx)
    ctx.papers.create({t.id: "T"})
    d = ctx.fs.backups_dir
    for i in range(5):
        (d / f"litmgr_2026010{i + 1}_000000.db").write_bytes(b"x")
    keep_files = [d / "litmgr_20250101_000000_premigrate_v2.db", d / "litmgr_20250101_000001_manual.db"]
    for k in keep_files:
        k.write_bytes(b"x")
    old = time.time() - 48 * 3600
    for p in d.glob("litmgr_*.db"):
        os.utime(p, (old, old))
    ctx.backup.auto_backup(keep=2)
    assert all(k.exists() for k in keep_files)
    autos = [p for p in d.glob("litmgr_*.db") if p.name.count("_") == 2]
    assert len(autos) == 2
