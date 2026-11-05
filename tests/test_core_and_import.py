"""核心功能测试：字段类型、字段管理、卡片解析、文件配对、导入、检索、历史、备份。

其中用到用户真实论文目录的测试，在目录不存在时自动跳过。
"""

from pathlib import Path

import pytest

from litmgr.core.field_types import get_type
from litmgr.importers.card_parser import parse_card_text, read_text_file
from litmgr.importers.file_pairing import pair_files
from litmgr.services.app_context import AppContext
from litmgr.services.import_service import ACT_NEW, LabelDecision
from litmgr.services.search_service import Condition, SearchQuery

REAL = Path(r"D:\2file\研究生2026.9.7\零散论文")
needs_real = pytest.mark.skipif(not REAL.exists(), reason="真实论文目录不存在")


@pytest.fixture
def ctx(tmp_path):
    c = AppContext(tmp_path / "lib")
    yield c
    c.close()


# ---------- 字段类型 ----------
def test_field_types():
    assert get_type("date").parse("2023.4.17") == ("2023-04-17", "2023-04-17")
    assert get_type("date").parse("2024年6月")[0] == "2024-06"
    assert get_type("date").parse("2410")[1] is None          # 无法识别：保留原文
    assert get_type("tags").parse("a，b、a;c") == ("a、b、c", ["a", "b", "c"])
    assert get_type("number").parse("10+5") == ("10+5", None)
    assert get_type("rating").parse("9")[1] == 5


# ---------- 字段管理 ----------
def test_default_fields_and_rename(ctx):
    fs = ctx.fields.list()
    assert len(fs) == 25
    title = ctx.fields.by_role("title")
    assert title.name == "中文标题"
    title.name = "标题"                      # 改名不影响角色绑定
    ctx.fields.update(title)
    assert ctx.fields.by_role("title").id == title.id


def test_field_archive_and_type_change(ctx):
    f = ctx.fields.add("评分备注", "text")
    pid = ctx.papers.create({f.id: "7"})
    f.type = "number"
    ctx.fields.update(f)
    assert ctx.papers.get(pid).values[f.id].json == 7.0
    ctx.fields.archive(f.id)
    assert f.id not in [x.id for x in ctx.fields.list()]
    ctx.fields.restore(f.id)
    assert ctx.papers.get(pid).text_of(f.id) == "7"   # 归档不丢数据


# ---------- 卡片解析 ----------
def test_parse_multiline_and_numbered():
    known = {"中文标题": 1, "研究问题": 2, "代码地址": 3}
    text = ("中文标题：A\n研究问题：问题一\n续行\n\n续行2\n代码地址：https://x.com/a\n"
            "https://y.com/b\n(5)我的疑问：什么\n第一条路线：模块化\n")
    known = {k.casefold(): v for k, v in known.items()}
    parsed = parse_card_text(text, known)
    by = {e.label: e for e in parsed.entries}
    assert by["研究问题"].content == "问题一\n续行\n\n续行2"
    assert "https://y.com/b" in by["代码地址"].content          # URL 行不被当成标签
    assert by["我的疑问"].numbered and by["我的疑问"].field_id is None
    # 又短又无标点的“xx：yy”无法与真字段区分，只会被标成“猜测型”未知标签，
    # 导入向导默认把它并回上一字段（不丢内容）
    assert by["第一条路线"].guess and by["第一条路线"].field_id is None


@needs_real
def test_parse_real_cards(ctx):
    lookup = ctx.fields.name_lookup()
    d = REAL / "论文卡片"
    rt = parse_card_text(read_text_file(next(d.glob("RT-DocLayout*"))), lookup)
    labels = {e.label for e in rt.entries}
    assert "当前发表状态" in labels                              # 模板外字段 -> 未知标签
    title_f = ctx.fields.by_role("title")
    assert "RT-DocLayout" in rt.known_text(title_f.id)
    old = parse_card_text(read_text_file(next(d.glob("文档解析揭秘*"))), lookup)
    assert title_f.id in {e.field_id for e in old.entries}        # (1)中文标题 编号格式
    assert any(e.label == "我的疑问" and e.numbered for e in old.entries)


# ---------- 文件配对 ----------
@needs_real
def test_pairing_real_files():
    paths = [REAL, ]
    groups = pair_files([REAL / "论文卡片", REAL / "零散论文翻译"] +
                        list(REAL.glob("*.pdf")))
    rt = next(g for g in groups if "RT-DocLayout" in g.title_hint)
    assert rt.card and rt.translations
    assert {p.subtype for p in rt.pdfs} == {"正文", "补充材料"}   # 补充材料(编号不同)也能配上
    detr = next(g for g in groups if "DETRs" in g.title_hint)
    assert len(detr.pdfs) == 2 and detr.card and detr.translations


# ---------- 导入 + 检索 ----------
@needs_real
def test_import_and_search(ctx):
    plan = ctx.imports.build_plan([REAL / "论文卡片", REAL / "零散论文翻译"] +
                                  list(REAL.glob("*.pdf")))
    cards = [i for i in plan.items if i.parsed]
    assert len([i for i in cards if i.action == "import"]) == len(cards) - 1  # 只有空模板被跳过
    assert any("卡片内容全为空" in "".join(i.warnings) for i in cards)
    labels = {u.label for u in plan.unknown}
    assert "当前发表状态" in labels
    res = ctx.imports.execute(plan, {
        next(u.key for u in plan.unknown if u.label == "当前发表状态"):
            LabelDecision(ACT_NEW, new_type="select")})
    assert not res.errors and len(res.created) >= 4
    assert any(f.name == "当前发表状态" for f in ctx.fields.list())

    # 再导入一次：重复论文默认跳过
    plan2 = ctx.imports.build_plan([REAL / "论文卡片"])
    assert all(i.action == "skip" for i in plan2.items if i.parsed)

    hits = ctx.search.run(SearchQuery(text="阅读顺序"))
    assert any("RT-DocLayout" in p.title for p in hits)
    assert ctx.search.run(SearchQuery(text="RT")), "1~2 字符查询应回退到 LIKE"
    # 只在字段内搜索（不含翻译正文/笔记）
    only_fields = ctx.search.run(SearchQuery(text="阅读顺序", include_fulltext=False))
    assert only_fields
    # 条件过滤
    venue = next(f for f in ctx.fields.list() if f.name == "论文所属会议/期刊")
    cvpr = ctx.search.run(SearchQuery(conditions=[Condition(venue.id, "contains", "CVPR")]))
    assert any("DETR" in p.title for p in cvpr)
    # 翻译正文索引：公式/正文内容也能搜到
    assert ctx.search.run(SearchQuery(text="Uncertainty-minimal"))


# ---------- 修改历史与撤销 ----------
def test_history_undo(ctx):
    f = ctx.fields.by_role("title")
    pid = ctx.papers.create({f.id: "旧标题"})
    ctx.papers.set_field(pid, f.id, "新标题")
    assert ctx.papers.get(pid).title == "新标题"
    ctx.history.undo_last()
    assert ctx.papers.get(pid).title == "旧标题"
    assert ctx.history.undo_last() is None


# ---------- 整理 / 对比 / 导出 / 备份 ----------
def test_organize_compare_export_backup(ctx, tmp_path):
    t = ctx.fields.by_role("title")
    a = ctx.papers.create({t.id: "论文A"})
    b = ctx.papers.create({t.id: "论文B"})
    ctx.organize.tag_papers([a], "待精读")
    cid = ctx.organize.add_collection("版面分析")
    ctx.organize.add_to_collection([a, b], cid)
    assert [p.id for p in ctx.search.run(SearchQuery(tag_ids=[ctx.organize.tags()[0].id]))] == [a]
    assert len(ctx.search.run(SearchQuery(collection_id=cid))) == 2
    ctx.organize.save_view("测试", SearchQuery(text="论文"))
    assert ctx.organize.query_of(ctx.organize.views()[0]).text == "论文"

    table = ctx.compare.build([a, b])
    row = next(r for r in table.rows if r.field.id == t.id)
    assert not row.all_same and row.cells == ["论文A", "论文B"]
    out = ctx.export.export("txt", [a], tmp_path / "out")
    assert out[0].read_text(encoding="utf-8").startswith("一句话总结论文主要内容：")
    ctx.export.export("csv", [a, b], tmp_path / "x.csv")

    bk = ctx.backup.backup_now()
    ctx.papers.delete(a)
    ctx.backup.restore(bk)
    assert ctx.papers.count() == 2
