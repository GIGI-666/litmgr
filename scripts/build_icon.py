"""从可编辑 SVG 生成文献管理系统图标与尺寸预览。

【作用】生成透明 PNG、包含多个尺寸的 Windows ICO，以及浅色/深色背景预览图。
【职责】所有尺寸直接从 SVG 栅格化，避免小图放大模糊；ICO 内嵌 PNG 并校验目录结构。
【依赖】PySide6.QtSvg / QtGui 和标准库 struct，不添加 Pillow 等运行依赖。
【被谁调用】维护者修改 litmgr/assets/app-icon.svg 后手动运行；应用只读取成品。
【扩展点】尺寸列表和预览布局在本文件维护，视觉设计只改 SVG。
"""

from __future__ import annotations

import os
from pathlib import Path
import struct

from PySide6.QtCore import QBuffer, QIODevice, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)


def render_icon(renderer: QSvgRenderer, size: int) -> QImage:
    """从矢量源绘制一张带透明通道的图标。"""
    image = QImage(size, size, QImage.Format_ARGB32_Premultiplied)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()
    return image


def png_bytes(image: QImage) -> bytes:
    """将 QImage 编码为 PNG 字节，供 ICO 目录引用。"""
    buffer = QBuffer()
    buffer.open(QIODevice.WriteOnly)
    if not image.save(buffer, "PNG"):
        raise ValueError("PNG 编码失败")
    return bytes(buffer.data())


def build_icon(source: Path, output: Path, preview: Path) -> None:
    """生成 512px PNG、九尺寸 ICO 和预览；目录自动建立。"""
    renderer = QSvgRenderer(str(source))
    if not renderer.isValid():
        raise ValueError(f"无效 SVG：{source}")
    output.mkdir(parents=True, exist_ok=True)
    master = render_icon(renderer, 512)
    if not master.save(str(output / "app-icon.png")):
        raise OSError("无法写入主 PNG 图标")
    frames = [(size, png_bytes(render_icon(renderer, size))) for size in SIZES]
    offset = 6 + len(frames) * 16
    directory = bytearray(struct.pack("<HHH", 0, 1, len(frames)))
    for size, payload in frames:
        dimension = size if size < 256 else 0
        directory.extend(struct.pack("<BBBBHHII", dimension, dimension, 0, 0, 1, 32, len(payload), offset))
        offset += len(payload)
    (output / "app-icon.ico").write_bytes(bytes(directory) + b"".join(payload for _, payload in frames))

    # 预览兼顾应用图标大图和标题栏/任务栏实际尺寸，浅深背景各展示一次。
    sheet = QImage(880, 480, QImage.Format_ARGB32_Premultiplied)
    sheet.fill(QColor("#F3F6FB"))
    painter = QPainter(sheet)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setFont(QFont("Microsoft YaHei UI", 18, QFont.DemiBold))
    painter.setPen(QColor("#18315C"))
    painter.drawText(36, 45, "litmgr  ·  文献管理系统")
    painter.drawImage(QRectF(35, 86, 285, 285), master)
    painter.setFont(QFont("Microsoft YaHei UI", 10))
    painter.setPen(QColor("#5B6B82"))
    painter.drawText(58, 411, "文献叠页  /  L 形版面  /  书签")
    for top, color, ink in ((86, "#FFFFFF", "#4D5F7A"), (257, "#172338", "#C1CEE1")):
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(color))
        painter.drawRoundedRect(QRectF(355, top, 488, 148), 18, 18)
        for left, size in ((382, 16), (434, 24), (494, 32), (563, 48), (648, 64), (744, 80)):
            painter.drawImage(QRectF(left, top + 21 + (80 - size) / 2, size, size),
                              render_icon(renderer, size))
            painter.setPen(QColor(ink))
            painter.drawText(QRectF(left - 6, top + 111, max(size, 32) + 12, 22), Qt.AlignCenter, str(size))
        painter.setPen(Qt.NoPen)
    painter.end()
    preview.parent.mkdir(parents=True, exist_ok=True)
    if not sheet.save(str(preview)):
        raise OSError("无法写入图标预览")


def main() -> None:
    """命令行入口，不启动桌面窗口，直接重建仓库中的图标资产。"""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    if os.name == "nt":
        os.environ.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")
    app = QGuiApplication.instance() or QGuiApplication([])
    root = Path(__file__).resolve().parents[1]
    build_icon(root / "litmgr/assets/app-icon.svg", root / "litmgr/assets",
               root / "planning/assets/app-icon-preview.png")
    print(f"Built PNG, ICO ({len(SIZES)} sizes), preview; Qt: {app.platformName()}")


if __name__ == "__main__":
    main()
