"""环境自检脚本：运行 `python scripts/check_env.py` 检查本系统依赖的组件是否可用。

检查项：SQLite FTS5 trigram（中文全文检索）、PySide6、QtPdf（PDF 查看）、
QtWebEngine（Markdown + 公式渲染）、markdown-it-py、KaTeX 资源。
"""

import sqlite3
import sys
from pathlib import Path


def check(name, fn):
    try:
        detail = fn()
        print(f"[OK]   {name}" + (f"  {detail}" if detail else ""))
        return True
    except Exception as e:  # noqa: BLE001
        print(f"[FAIL] {name}: {e}")
        return False


def sqlite_trigram():
    c = sqlite3.connect(":memory:")
    c.execute("create virtual table t using fts5(a, tokenize='trigram')")
    c.execute("insert into t values ('文档版面分析')")
    assert c.execute("select count(*) from t where t match '\"版面分\"'").fetchone()[0] == 1
    return f"SQLite {sqlite3.sqlite_version}"


def pyside():
    import PySide6
    return PySide6.__version__


def qtpdf():
    from PySide6.QtPdf import QPdfDocument  # noqa: F401
    from PySide6.QtPdfWidgets import QPdfView  # noqa: F401


def webengine():
    from PySide6.QtWebEngineWidgets import QWebEngineView  # noqa: F401


def md():
    import markdown_it
    import mdit_py_plugins  # noqa: F401
    return f"markdown-it-py {markdown_it.__version__}"


def katex():
    d = Path(__file__).resolve().parent.parent / "litmgr" / "assets" / "katex"
    assert (d / "katex.min.js").exists(), f"缺少 {d / 'katex.min.js'}"


if __name__ == "__main__":
    results = [check("SQLite trigram 全文检索", sqlite_trigram), check("PySide6", pyside),
               check("QtPdf (PDF 查看)", qtpdf), check("QtWebEngine (网页渲染)", webengine),
               check("markdown-it-py", md), check("KaTeX 本地资源", katex)]
    sys.exit(0 if all(results) else 1)
