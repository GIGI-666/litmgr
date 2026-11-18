"""主窗口右侧的论文预览面板。

【作用】显示选中论文的标题、状态、标签/分组、各字段摘要与文件列表；
    下方有“打开详情”“阅读”两个按钮，通过信号通知主窗口（面板自己不开窗口）。
【依赖】services（经 AppContext）；core.models。
【被谁调用】ui.main_window。
"""

from __future__ import annotations

import html as h

from PySide6.QtCore import QAbstractAnimation, QEasingCurve, QPropertyAnimation, Signal
from PySide6.QtWidgets import QGraphicsOpacityEffect, QHBoxLayout, QTextBrowser, QVBoxLayout, QWidget

from ..core.models import KIND_LABELS, READ_STATUS
from ..services.app_context import AppContext
from .motion import FADE_DURATION_MS, FADE_START_OPACITY, motion_preference
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
        self._selection: tuple[int, ...] = ()
        self._fade_effect = QGraphicsOpacityEffect(self.browser.viewport())
        self._fade_effect.setEnabled(False)
        self.browser.viewport().setGraphicsEffect(self._fade_effect)
        self._fade = QPropertyAnimation(self._fade_effect, b"opacity", self)
        self._fade.setDuration(FADE_DURATION_MS)
        self._fade.setStartValue(FADE_START_OPACITY)
        self._fade.setEndValue(1.0)
        self._fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade.finished.connect(self._finish_fade)
        self._motion = motion_preference()
        self._motion.changed.connect(self._on_motion_changed)
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
        selection = tuple(ids)
        changed = selection != self._selection
        self._selection = selection
        self.open_btn.setEnabled(len(ids) == 1)
        self.read_btn.setEnabled(bool(ids))
        if len(ids) == 1 and self.ctx.papers.exists(ids[0]):
            self.browser.setHtml(self._paper_html(ids[0]))
        elif len(ids) > 1:
            self.browser.setHtml(f"<p>已选中 <b>{len(ids)}</b> 篇论文。<br>"
                                 "可右键批量操作，或点工具栏“对比选中论文”。</p>")
        else:
            self.browser.setHtml("<p>选中一篇论文查看预览；双击或回车打开详情。</p>")
        if (changed and self.isVisible() and self._motion.enabled
                and self._fade.state() != QAbstractAnimation.State.Running):
            self._fade_effect.setOpacity(FADE_START_OPACITY)
            self._fade_effect.setEnabled(True)
            self._fade.start()

    def _finish_fade(self) -> None:
        self._fade_effect.setEnabled(False)

    def _on_motion_changed(self, enabled: bool) -> None:
        if not enabled:
            self._fade.stop()
            self._finish_fade()

    def _paper_html(self, paper_id: int) -> str:
        p = self.ctx.papers.get(paper_id)
        tags = "、".join(t.name for t in self.ctx.organize.tags_of(paper_id)) or "无"
        cols = "、".join(c.name for c in self.ctx.organize.collections_of(paper_id)) or "无"
        parts = [f"<h3>{h.escape(p.title)}</h3>",
                 f"<p>{READ_STATUS.get(p.read_status, '')}　"
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
