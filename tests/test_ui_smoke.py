"""界面冒烟测试（离屏）：各窗口能创建、能响应事件刷新、编辑字段能保存。不涉及 WebEngine。"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication  # noqa: E402

from litmgr.services.app_context import AppContext  # noqa: E402
from litmgr.ui.window_manager import WindowManager  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def env(app, tmp_path):
    ctx = AppContext(tmp_path / "lib")
    wm = WindowManager(ctx)
    yield ctx, wm
    wm.close_all()
    ctx.close()


def test_main_detail_compare(env):
    ctx, wm = env
    title = ctx.fields.by_role("title")
    a = ctx.papers.create({title.id: "论文A"})
    b = ctx.papers.create({title.id: "论文B"})
    main = wm.open_main(None)
    main.refresh()
    assert main.table.paper_count() == 2

    # 详情窗口：编辑字段 -> 保存 -> 主列表刷新
    d = wm.open_detail(a)
    assert wm.open_detail(a) is d                      # 同一篇论文复用窗口
    d.form.editors[title.id].edit.setText("论文A（改）")
    d.form.editors[title.id]._commit()
    assert ctx.papers.get(a).title == "论文A（改）"
    main._refresh_timer.timeout.emit()
    assert any(p.title == "论文A（改）" for p in main.table.model_.papers)

    # 外部修改（如撤销）-> 详情窗口自动刷新
    ctx.history.undo_last()
    assert d.title_label.text() == "论文A"

    # 对比窗口：双击单元格编辑 -> 写回
    c = wm.open_compare([a, b])
    assert c.table.columnCount() == 2
    c.table.item(0, 0).setText("x")  # 触发 itemChanged（第一行是第一个字段）
    assert any(p.text_of(c.table.item(0, 0).data(256)[1]) == "x" for p in ctx.papers.list_all())

    # 笔记：保存 -> 可被全文检索；修改历史面板能列出并撤销
    d.note_panel.edit.setPlainText("这是一条关于阅读顺序的笔记")
    d.note_panel.save()
    from litmgr.services.search_service import SearchQuery
    assert [p.id for p in ctx.search.run(SearchQuery(text="关于阅读顺序"))] == [a]
    ctx.papers.set_field(a, title.id, "论文A-v2")
    d.history_panel.refresh()
    assert d.history_panel.tree.topLevelItemCount() >= 1
    d.history_panel.tree.setCurrentItem(d.history_panel.tree.topLevelItem(0))
    d.history_panel.undo_selected()
    assert ctx.papers.get(a).title == "x"   # 恢复到上一次（对比窗口里改成的）值

    # 字段管理：新增字段后详情页重建
    n_before = len(d.form.editors)
    ctx.fields.add("新字段", "rating")
    assert len(d.form.editors) == n_before + 1

    # 删除论文 -> 详情窗口自动关闭
    ctx.papers.delete(a)
    assert a not in wm._detail
