"""Markdown 查看器（支持表格与 LaTeX 公式）。

【作用】显示翻译 md：标题、段落、表格、代码块、行内公式 `$...$` 与块级公式 `$$...$$`。
【实现】
    - markdown-it-py 把 md 转成 HTML（含 dollarmath 插件识别公式）
    - 写入临时 HTML 文件，用 QtWebEngine 加载；公式由本地 KaTeX（assets/katex）渲染，完全离线
    - 内置页内查找、字号缩放
    - 用临时文件而不是 setHtml，避免大文档超过 setHtml 的 2MB 限制
【依赖】PySide6.QtWebEngineWidgets；markdown-it-py、mdit-py-plugins；assets/katex。
【被谁调用】ui.reader_window。
"""

from __future__ import annotations

import hashlib
import html
import tempfile
from pathlib import Path

import shiboken6
from markdown_it import MarkdownIt
from mdit_py_plugins.dollarmath import dollarmath_plugin
from PySide6.QtCore import QTimer, QUrl
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

KATEX_DIR = Path(__file__).resolve().parent.parent / "assets" / "katex"

# 读取/设置页面滚动比例的小脚本（0 = 顶部，1 = 底部）
_JS_GET_FRAC = ("window.scrollY / Math.max(1, document.documentElement.scrollHeight"
                " - window.innerHeight)")
_JS_SET_FRAC = ("window.scrollTo(0, %r * Math.max(0, document.documentElement.scrollHeight"
                " - window.innerHeight))")

_PAGE = """<!doctype html>
<html><head><meta charset="utf-8">
<link rel="stylesheet" href="{katex_css}">
<style>
  body {{ font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif; line-height: 1.75;
         max-width: 920px; margin: 0 auto; padding: 18px 26px 80px; color: #222; }}
  h1, h2, h3, h4 {{ line-height: 1.35; margin: 1.4em 0 .6em; }}
  h1 {{ font-size: 1.6em; border-bottom: 2px solid #e3e7ee; padding-bottom: .25em; }}
  h2 {{ font-size: 1.35em; border-bottom: 1px solid #e3e7ee; padding-bottom: .2em; }}
  table {{ border-collapse: collapse; margin: 1em 0; font-size: .95em; }}
  th, td {{ border: 1px solid #ccd3de; padding: 5px 10px; }}
  th {{ background: #f1f4f9; }}
  code {{ background: #f3f4f6; padding: 1px 4px; border-radius: 3px; }}
  pre {{ background: #f3f4f6; padding: 10px; overflow-x: auto; border-radius: 4px; }}
  blockquote {{ border-left: 4px solid #cfd6e2; margin-left: 0; padding-left: 14px; color: #555; }}
  .math.block {{ overflow-x: auto; margin: .8em 0; text-align: center; }}
  img {{ max-width: 100%; }}
</style></head>
<body>{body}
<script src="{katex_js}"></script>
<script>
  document.querySelectorAll('.math').forEach(function (el) {{
    try {{
      katex.render(el.textContent, el, {{displayMode: el.classList.contains('block'),
                                         throwOnError: false}});
    }} catch (e) {{ /* 公式有误时保留原文 */ }}
  }});
</script></body></html>"""


_MD: MarkdownIt | None = None


def render_markdown(text: str) -> str:
    """md -> HTML 片段（公式保留为 .math 元素，交给页面里的 KaTeX 渲染）。"""
    global _MD
    if _MD is None:      # 解析器配置一次即可复用，不必每次打开都重新构建
        _MD = (MarkdownIt("commonmark", {"html": True, "breaks": False})
               .enable("table").enable("strikethrough")
               .use(dollarmath_plugin, allow_space=True, allow_digits=True, double_inline=True))
    return _MD.render(text)


def build_page(text: str) -> str:
    return _PAGE.format(katex_css=(KATEX_DIR / "katex.min.css").as_uri(),
                        katex_js=(KATEX_DIR / "katex.min.js").as_uri(),
                        body=render_markdown(text))


_CACHE_PREFIX = "page_"
_CACHE_VERSION = "v1|"      # 页面模板/渲染方式变化时改动，使旧缓存自动失效
_CACHE_KEEP = 40            # 最多保留多少个缓存页面


def _prune_cache(directory: Path) -> None:
    """清理缓存目录：只保留最近使用的若干页面，并顺手删掉旧版本留下的临时文件。"""
    try:
        pages = sorted(directory.glob(f"{_CACHE_PREFIX}*.html"), key=lambda p: p.stat().st_mtime,
                       reverse=True)
        for old in pages[_CACHE_KEEP:]:
            old.unlink(missing_ok=True)
        for legacy in directory.glob("view_*.html"):
            legacy.unlink(missing_ok=True)
    except OSError:
        pass   # 清理失败不影响阅读


_warm_page: QWebEnginePage | None = None


def prewarm() -> None:
    """提前启动 QtWebEngine（浏览器进程、默认配置），让第一次打开阅读窗口不用再等。

    程序启动、主窗口显示后空闲时调用一次；退出前调用 release_prewarm()。
    """
    global _warm_page
    if _warm_page is None:
        _warm_page = QWebEnginePage()
        _warm_page.setHtml("<html></html>")


def release_prewarm() -> None:
    """释放预热用的页面（必须在 QApplication 结束前，否则 WebEngine 会报告资源未释放）。"""
    global _warm_page
    if _warm_page is not None:
        shiboken6.delete(_warm_page)
        _warm_page = None


class MarkdownViewer(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        bar = QHBoxLayout()
        self.find_edit = QLineEdit()
        self.find_edit.setPlaceholderText("在翻译中查找（回车下一个）")
        self.find_edit.setMaximumWidth(260)
        self.find_edit.returnPressed.connect(lambda: self.find(True))
        prev_b, next_b = QPushButton("↑"), QPushButton("↓")
        prev_b.clicked.connect(lambda: self.find(False))
        next_b.clicked.connect(lambda: self.find(True))
        zin, zout = QPushButton("A＋"), QPushButton("A－")
        zin.clicked.connect(lambda: self.zoom(1.1))
        zout.clicked.connect(lambda: self.zoom(1 / 1.1))
        for w in (QLabel("翻译："), self.find_edit, prev_b, next_b, zout, zin):
            bar.addWidget(w)
        bar.addStretch(1)
        lay.addLayout(bar)
        self.web = QWebEngineView()
        lay.addWidget(self.web, 1)
        self._dir = Path(tempfile.gettempdir()) / "litmgr_view"
        self._dir.mkdir(exist_ok=True)
        _prune_cache(self._dir)
        # 阅读位置：用“滚动比例(0~1)”表示，缩放后也仍然对得上
        self._frac = 0.0
        self._pending_frac: float | None = None
        self._frac_timer = QTimer(self)
        self._frac_timer.setSingleShot(True)
        self._frac_timer.setInterval(250)
        self._frac_timer.timeout.connect(self._capture_frac)
        self.web.page().scrollPositionChanged.connect(lambda _p: self._frac_timer.start())
        self.web.loadFinished.connect(self._on_load_finished)

    # ---------- 阅读状态（供“阅读历史”保存/还原） ----------
    def get_state(self) -> dict:
        return {"frac": self._frac, "zoom": self.web.zoomFactor()}

    def apply_state(self, state: dict) -> None:
        """还原滚动位置与字号；需在 load_text() 之前或之后紧接着调用。"""
        if not state:
            return
        self.web.setZoomFactor(max(0.4, min(3.0, float(state.get("zoom", 1.0)))))
        self._pending_frac = max(0.0, min(1.0, float(state.get("frac", 0.0))))

    def _capture_frac(self) -> None:
        self.web.page().runJavaScript(_JS_GET_FRAC, self._store_frac)

    def _store_frac(self, value) -> None:
        if isinstance(value, (int, float)):
            self._frac = float(value)

    def _on_load_finished(self, ok: bool) -> None:
        frac, self._pending_frac = self._pending_frac, None
        if not ok or frac is None:
            return
        self._frac = frac
        # 公式渲染/字体加载会让页面高度在加载后略有变化，稍等片刻再滚动
        QTimer.singleShot(150, self, lambda: self.web.page().runJavaScript(_JS_SET_FRAC % frac))

    def load_text(self, text: str) -> None:
        """显示一段 markdown 文本。"""
        # 页面按“内容哈希”缓存：同一份翻译再次打开（如从最近阅读还原）直接复用，跳过耗时的渲染；
        # 文件名由内容决定，也就不会出现加载时被覆盖的问题
        # （KaTeX 的路径也计入：程序文件夹挪动后，页面里写死的资源路径会变，旧缓存要失效）
        key = hashlib.sha1(
            f"{_CACHE_VERSION}{KATEX_DIR}|{text}".encode("utf-8", "surrogatepass")).hexdigest()
        f = self._dir / f"{_CACHE_PREFIX}{key}.html"
        if not f.exists():
            f.write_text(build_page(text), encoding="utf-8")
        else:
            f.touch()    # 刷新“最近使用”时间，清理时优先保留
        self.web.setUrl(QUrl.fromLocalFile(str(f)))

    def show_message(self, text: str) -> None:
        self.web.setHtml(f"<body style='font-family:sans-serif;color:#777;padding:30px'>"
                         f"{html.escape(text)}</body>")

    def find(self, forward: bool = True) -> None:
        text = self.find_edit.text()
        flags = QWebEnginePage.FindFlag(0) if forward else QWebEnginePage.FindFlag.FindBackward
        self.web.findText(text, flags)

    def zoom(self, factor: float) -> None:
        self.web.setZoomFactor(max(0.4, min(3.0, self.web.zoomFactor() * factor)))
