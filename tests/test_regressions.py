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

from PySide6.QtCore import QMarginsF, Qt  # noqa: E402
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


# ---------- 第六轮：健壮性与体验 ----------
def test_safe_filename_reserved_names():
    from litmgr.core.textutil import safe_filename
    assert safe_filename("CON") != "CON" and safe_filename("nul.txt").startswith("_")
    assert safe_filename("abc") == "abc"


def test_config_atomic_save_and_tolerant_load(tmp_path, monkeypatch):
    from litmgr.core.config import AppConfig
    monkeypatch.setenv("LITMGR_HOME", str(tmp_path))
    c = AppConfig()
    c.remember_library("X")
    c.save()
    assert not (tmp_path / "config.json.tmp").exists()
    assert AppConfig.load().library_path == "X"
    (tmp_path / "config.json").write_text("[1,2]", encoding="utf-8")
    assert AppConfig.load().library_path == ""
    (tmp_path / "config.json").write_text('{"ui_state": 5, "backup_keep": "x"}', encoding="utf-8")
    cfg = AppConfig.load()
    assert cfg.ui_state == {} and cfg.backup_keep == 10


def test_add_file_recopies_truncated_target(ctx, tmp_path):
    src = tmp_path / "a.pdf"
    src.write_bytes(b"%PDF-full-content")
    pid = ctx.papers.create({_title(ctx).id: "T"})
    f = ctx.files.add(pid, "pdf", src)
    target = ctx.fs.abs_path(f.rel_path)
    target.write_bytes(b"%PDF")        # 模拟复制中断留下的半截文件
    ctx.fs.add_file(pid, "pdf", src)
    assert target.read_bytes() == src.read_bytes()


def test_find_and_delete_orphans(ctx, tmp_path):
    src = tmp_path / "a.pdf"
    src.write_bytes(b"%PDF-1")
    pid = ctx.papers.create({_title(ctx).id: "T"})
    ctx.files.add(pid, "pdf", src)
    stray = ctx.fs.papers_dir / "999" / "pdf" / "x.pdf"
    stray.parent.mkdir(parents=True)
    stray.write_bytes(b"x")
    assert ctx.files.find_orphans() == [stray]
    assert ctx.files.delete_orphans([stray]) == 1
    assert not (ctx.fs.papers_dir / "999").exists()
    assert ctx.files.find_orphans() == []


def test_undo_is_atomic(ctx, monkeypatch):
    t = _title(ctx)
    p = ctx.papers.create({t.id: "A"})
    ctx.papers.set_field(p, t.id, "B")
    e = ctx.history.of_paper(p)[0]
    monkeypatch.setattr(ctx.history.log, "mark_undone",
                        lambda _i: (_ for _ in ()).throw(RuntimeError("boom")))
    with pytest.raises(RuntimeError):
        ctx.history.undo(e.id)
    assert ctx.papers.get(p).title == "B"      # 值也一并回滚


def test_fuzzy_pairing_flagged(tmp_path):
    from litmgr.importers.file_pairing import pair_files
    for n in ("Attention Is All You Need2017.pdf", "Attention Is All You Need.2017论文卡片.txt",
              "Totally Different Paper2020.pdf"):
        (tmp_path / n).write_bytes(b"x")
    gs = pair_files([tmp_path])
    assert len(gs) == 2


def test_import_progress_callback(ctx, tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "Foo Net2406.pdf").write_bytes(b"%PDF-1")
    plan = ctx.imports.build_plan([src])
    calls = []
    ctx.imports.execute(plan, progress=lambda d, n, t: calls.append((d, n)))
    assert calls[0] == (0, 1) and calls[-1] == (1, 1)


def test_compare_new_field_checked_and_filter_lock(app, ctx):
    from litmgr.ui.compare_window import CompareWindow
    from litmgr.ui.filter_dialog import FilterDialog
    from litmgr.core.query import SearchQuery
    p = ctx.papers.create({_title(ctx).id: "T"})
    w = CompareWindow(ctx, None, [p])
    ctx.fields.add("新加字段X", "text")
    items = {w.field_list.item(i).text(): w.field_list.item(i).checkState()
             for i in range(w.field_list.count())}
    assert items["新加字段X"] == Qt.Checked
    w.close()
    q = SearchQuery(read_status="read", include_archived=True)
    dlg = FilterDialog(None, ctx, q, lock_status=True)
    assert not dlg.status.isEnabled()
    dlg._clear()
    assert not dlg.archived.isChecked()
    q2 = SearchQuery(read_status="read")
    dlg.apply_to(q2)
    assert q2.read_status == "read"      # 锁定时不改写状态


# ---------- 字段分组：独立保存、迁移、同步和内容保护 ----------
def test_empty_field_group_survives_restart(tmp_path):
    """先建空分组，重启后仍可选择；字段编辑中直接输入的新分组也会保存。"""
    path = tmp_path / "groups_lib"
    c = AppContext(path)
    try:
        assert c.fields.groups() == ["概要", "基本信息", "内容", "实验", "我的思考"]
        assert c.fields.add_group("  复现记录  ") == "复现记录"
        f = c.fields.add("运行环境", group_name="代码复现")
        assert f.group_name == "代码复现"
    finally:
        c.close()
    c = AppContext(path)
    try:
        assert "复现记录" in c.fields.groups() and "代码复现" in c.fields.groups()
        c.fields.delete_group("复现记录")
        assert "复现记录" not in c.fields.groups()
    finally:
        c.close()


def test_field_groups_rename_delete_keep_values_and_archived_fields(ctx):
    """组改名及删除覆盖已归档字段；字段编号、顺序、内容和索引均保留。"""
    from litmgr.core.events import Events
    from litmgr.core.query import SearchQuery
    active = ctx.fields.add("复现结果", group_name="复现")
    archived = ctx.fields.add("旧复现记录", group_name="复现")
    pid = ctx.papers.create({_title(ctx).id: "A", active.id: "复现成功", archived.id: "原始记录"})
    ctx.fields.archive(archived.id)
    order = [(f.id, f.sort_order) for f in ctx.fields.list(include_archived=True)]
    events = []
    ctx.events.subscribe(Events.FIELDS_CHANGED, lambda **_kw: events.append(True))
    ctx.fields.rename_group("复现", "代码与复现")
    assert ctx.fields.get(active.id).group_name == "代码与复现"
    assert ctx.fields.get(archived.id).group_name == "代码与复现"
    ctx.fields.delete_group("代码与复现")
    assert ctx.fields.get(active.id).group_name == ctx.fields.get(archived.id).group_name == ""
    assert ctx.fields.get(archived.id).archived
    assert [(f.id, f.sort_order) for f in ctx.fields.list(include_archived=True)] == order
    paper = ctx.papers.get(pid)
    assert paper.text_of(active.id) == "复现成功" and paper.text_of(archived.id) == "原始记录"
    assert [p.id for p in ctx.search.run(SearchQuery(text="复现成功"))] == [pid]
    assert len(events) == 2


def test_field_group_names_checked_and_field_moves(ctx):
    """拒绝空名和重名；已有组的不同空白/大小写写法会归入同一组。"""
    from litmgr.core.errors import DuplicateError, NotFoundError, ValidationError
    for name in ("", "  ", "未分组"):
        with pytest.raises(ValidationError):
            ctx.fields.add_group(name)
    ctx.fields.add_group("Code Notes")
    with pytest.raises(DuplicateError):
        ctx.fields.add_group(" codenotes ")
    with pytest.raises(DuplicateError):
        ctx.fields.rename_group("Code Notes", "概要")
    with pytest.raises(ValidationError):
        ctx.fields.rename_group("Code Notes", " ")
    with pytest.raises(NotFoundError):
        ctx.fields.delete_group("不存在")
    field = ctx.fields.add("复现进度", group_name=" code notes ")
    assert field.group_name == "Code Notes"
    field.group_name = "实验"
    ctx.fields.update(field)
    assert ctx.fields.get(field.id).group_name == "实验"
    assert "Code Notes" in ctx.fields.groups()  # 移走最后一个字段后仍保留空组


@pytest.mark.parametrize("action", ["rename", "delete"])
def test_field_group_changes_are_atomic(ctx, monkeypatch, action):
    """改名/删除中途失败时，组名和字段归属必须一起回滚，且不发成功事件。"""
    from litmgr.core.events import Events
    field = ctx.fields.add("回滚字段", group_name="回滚分组")
    events = []
    ctx.events.subscribe(Events.FIELDS_CHANGED, lambda **_kw: events.append(True))
    real_execute = ctx.db.execute

    def failing_execute(sql, params=()):
        if ((action == "rename" and sql.startswith("UPDATE field_def")) or
                (action == "delete" and sql.startswith("DELETE FROM field_group"))):
            raise RuntimeError("模拟分组操作中断")
        return real_execute(sql, params)

    monkeypatch.setattr(ctx.db, "execute", failing_execute)
    with pytest.raises(RuntimeError):
        if action == "rename":
            ctx.fields.rename_group("回滚分组", "新分组")
        else:
            ctx.fields.delete_group("回滚分组")
    assert "回滚分组" in ctx.fields.groups() and "新分组" not in ctx.fields.groups()
    assert ctx.fields.get(field.id).group_name == "回滚分组"
    assert events == []


def test_field_groups_migrate_from_v3_and_restore(ctx, tmp_path):
    """真实 v3 库没有分组表：恢复时迁移旧分组，包括仅有已归档字段的组。"""
    field = ctx.fields.add("旧库字段", group_name="旧库专用组")
    pid = ctx.papers.create({_title(ctx).id: "旧库论文", field.id: "应保留的内容"})
    ctx.fields.archive(field.id)
    old = tmp_path / "v3.db"
    dst = sqlite3.connect(old)
    ctx.db.conn.backup(dst)
    dst.execute("DROP TABLE field_group")
    dst.execute("PRAGMA user_version=3")
    dst.commit()
    dst.close()
    ctx.fields.add_group("只在当前库中")
    ctx.backup.restore(old)
    assert ctx.db.query_one("PRAGMA user_version")[0] == 4
    assert "旧库专用组" in ctx.fields.groups() and "只在当前库中" not in ctx.fields.groups()
    assert ctx.papers.get(pid).text_of(field.id) == "应保留的内容"
    assert list(ctx.fs.backups_dir.glob("*_premigrate_v3.db"))


def test_field_group_dialog_and_filtered_field_editor(app, ctx, monkeypatch):
    """界面可新建、改名、删除分组，并在所选分组内新建/移动字段。"""
    from PySide6.QtWidgets import QAbstractItemView, QInputDialog, QMessageBox
    from litmgr.ui.field_group_dialog import FieldGroupDialog
    from litmgr.ui.field_manager_dialog import FieldEditDialog, FieldManagerDialog
    from litmgr.ui.field_form import PaperFieldForm, _CollapsibleGroup
    group_dialog = FieldGroupDialog(None, ctx)
    manager = FieldManagerDialog(None, ctx)
    try:
        monkeypatch.setattr(QInputDialog, "getText", lambda *_a, **_kw: ("复现", True))
        group_dialog.add()
        manager.refresh()
        manager.group_filter.setCurrentIndex(manager.group_filter.findData("复现"))
        assert manager.list.count() == 0
        assert manager.list.dragDropMode() == QAbstractItemView.NoDragDrop
        editor = FieldEditDialog(manager, ctx, None, default_group="复现")
        editor.name.setText("复现说明")
        assert editor.group.currentText() == "复现"
        editor.accept()
        manager.refresh()
        assert manager.list.count() == 1
        fid = manager.list.item(0).data(Qt.UserRole)
        pid = ctx.papers.create({_title(ctx).id: "界面论文", fid: "保留内容"})
        monkeypatch.setattr(QInputDialog, "getText", lambda *_a, **_kw: ("复现进展", True))
        group_dialog.rename()
        assert ctx.fields.get(fid).group_name == "复现进展"
        monkeypatch.setattr(QMessageBox, "question", lambda *_a, **_kw: QMessageBox.Yes)
        group_dialog.delete()
        manager.refresh()
        manager.group_filter.setCurrentIndex(manager.group_filter.findData(""))
        assert any(manager.list.item(i).data(Qt.UserRole) == fid for i in range(manager.list.count()))
        form = PaperFieldForm(ctx, pid)
        assert "未分组" in [g.title() for g in form.widget().findChildren(_CollapsibleGroup)]
        assert form.editors[fid].text() == "保留内容"
        form.close()
        editor = FieldEditDialog(manager, ctx, ctx.fields.get(fid))
        editor.group.setCurrentText("实验")
        editor.accept()
        assert ctx.fields.get(fid).group_name == "实验"
    finally:
        group_dialog.close()
        manager.close()

