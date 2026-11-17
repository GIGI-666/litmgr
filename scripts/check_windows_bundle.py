"""对冻结后的 EXE 检查临时数据库、PDF 渲染及 WebEngine 离线公式。"""

import json
from pathlib import Path
import tempfile
import shiboken6

from PySide6.QtCore import QSize, QTimer
from PySide6.QtGui import QPainter, QPdfWriter
from PySide6.QtWidgets import QApplication

from litmgr.services.app_context import AppContext
from litmgr.ui.app_icon import configure_app_icon
from litmgr.ui.md_viewer import MarkdownViewer
from litmgr.ui.pdf_viewer import PdfViewer


def check_bundle(report_path: str) -> int:
    """仅使用临时目录验证发布包，将结果保存到指定 JSON。"""
    app = QApplication([])
    configure_app_icon(app)
    report = {"icon": not app.windowIcon().isNull()}
    with tempfile.TemporaryDirectory(prefix="litmgr-bundle-") as tmp:
        root = Path(tmp)
        ctx = AppContext(root / "library")
        report["database"] = ctx.db.query_one("PRAGMA user_version")[0] > 0
        writer = QPdfWriter(str(root / "sample.pdf"))
        painter = QPainter(writer)
        painter.drawText(100, 200, "Bundle PDF test")
        painter.end()
        del writer
        pdf = PdfViewer()
        report["pdf"] = pdf.load(str(root / "sample.pdf"))
        report["pdf_render"] = not pdf.doc.render(0, QSize(400, 600)).isNull()
        md = MarkdownViewer()
        md.show()

        def finish(ok=False):
            report["offline_formula"] = bool(ok)
            Path(report_path).write_text(json.dumps(report, indent=2), encoding="utf-8")
            app.exit(0 if all(report.values()) else 1)

        def loaded(ok):
            if not ok:
                finish()
                return
            md.web.page().runJavaScript(
                "typeof katex !== 'undefined' && !!document.querySelector('.katex')",
                finish,
            )

        md.web.loadFinished.connect(loaded)
        md.load_text("# Bundle test\n\n$x^2 + y^2 = z^2$\n")
        QTimer.singleShot(20000, finish)
        result = app.exec()
        md.close()
        md.web.setPage(None)
        pdf.close()
        pdf.doc.close()
        shiboken6.delete(pdf)
        shiboken6.delete(painter)
        app.processEvents()
        ctx.close()
        return result
