"""主窗口右侧的论文预览面板。

【作用】显示选中论文的标题、状态、标签/分组、各字段摘要与文件列表；
    下方有“打开详情”“阅读”两个按钮，通过信号通知主窗口（面板自己不开窗口）。
【依赖】services（经 AppContext）；core.models。
【被谁调用】ui.main_window。
"""

from __future__ import annotations

import html as h

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QTextBrowser, QVBoxLayout, QWidget

from ..core.models import KIND_LABELS, READ_STATUS
from ..services.app_context import AppContext
from .utils import make_button


class PreviewPanel(QWidget):
    openRequested = Signal()    # 点击“打开详情”
    readRequested = Signal()    # 点击“阅读”

    def __init__(self, ctx: AppContext, parent=None) -> None:
        super().__init__(parent)
        self.ctx = ctx
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(True)
        lay.addWidget(self.browser, 1)
        row = QHBoxLayout()
        self.open_btn = make_button("打开详情", self.openRequested.emit)
        self.read_btn = make_button("阅读", self.readRequested.emit)
        row.addWidget(self.open_btn)
        row.addWidget(self.read_btn)
        lay.addLayout(row)
        self.show_selection([])

    def show_selection(self, ids: list[int]) -> None:
        """按当前选中的论文 id 更新预览与按钮可用状态。"""
        self.open_btn.setEnabled(len(ids) == 1)
        self.read_btn.setEnabled(bool(ids))
        if len(ids) == 1 and self.ctx.papers.exists(ids[0]):
            self.browser.setHtml(self._paper_html(ids[0]))
        elif len(ids) > 1:
            self.browser.setHtml(f"<p style='color:#666'>已选中 <b>{len(ids)}</b> 篇论文。<br>"
                                 "可右键批量操作，或点工具栏“对比选中论文”。</p>")
        else:
            self.browser.setHtml("<p style='color:#888'>选中一篇论文查看预览；双击或回车打开详情。</p>")

    def _paper_html(self, paper_id: int) -> str:
        p = self.ctx.papers.get(paper_id)
        tags = "、".join(t.name for t in self.ctx.organize.tags_of(paper_id)) or "无"
        cols = "、".join(c.name for c in self.ctx.organize.collections_of(paper_id)) or "无"
        parts = [f"<h3>{h.escape(p.title)}</h3>",
                 f"<p style='color:#666'>{READ_STATUS.get(p.read_status, '')}　"
                 f"{'★' * p.rating}{'☆' * (5 - p.rating)}"
                 f"<br>标签：{h.escape(tags)}　分组：{h.escape(cols)}</p>"]
        for f in self.ctx.fields.list():
            text = p.text_of(f.id).strip()
            if text:
                short = text if len(text) <= 260 else text[:260] + "…"
                parts.append(f"<p><b>{h.escape(f.name)}</b><br>"
                             f"{h.escape(short).replace(chr(10), '<br>')}</p>")
        files = self.ctx.files.list(paper_id)
        if files:
            parts.append("<hr><p><b>文件</b><br>" + "<br>".join(
                f"[{KIND_LABELS[f.kind]}{('/' + f.subtype) if f.subtype else ''}] "
                f"{h.escape(f.display_name)}" for f in files) + "</p>")
        return "".join(parts)
