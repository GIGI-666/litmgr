"""文献库文件夹管理。

【作用】管理“文献库”这个文件夹的目录结构，负责把外部文件复制进库、解析库内路径。
【文献库结构】
    <文献库>/
        db/litmgr.db          数据库
        papers/<paper_id>/    每篇论文一个目录
            card/ pdf/ translation/ attachments/
        backups/              数据库自动备份
    整个文件夹复制走即可完成备份/迁移（数据库里只存相对路径）。
【依赖】仅标准库；core.models（文件种类常量）。
【被谁调用】services.app_context（创建）、import_service / paper_service（复制、删除文件）、
    ui（取绝对路径打开文件）。
【扩展点】新增文件种类时在 KIND_DIRS 增加映射。
"""

from __future__ import annotations

import hashlib
import re
import shutil
from pathlib import Path

from ..core.models import KIND_ATTACHMENT, KIND_CARD, KIND_PDF, KIND_TRANSLATION

KIND_DIRS = {
    KIND_CARD: "card",
    KIND_PDF: "pdf",
    KIND_TRANSLATION: "translation",
    KIND_ATTACHMENT: "attachments",
}
_BAD_CHARS = re.compile(r'[\\/:*?"<>|\r\n\t]+')


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class LibraryFS:
    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        self.db_dir = self.root / "db"
        self.papers_dir = self.root / "papers"
        self.backups_dir = self.root / "backups"
        for d in (self.db_dir, self.papers_dir, self.backups_dir):
            d.mkdir(parents=True, exist_ok=True)

    @property
    def db_path(self) -> Path:
        return self.db_dir / "litmgr.db"

    def abs_path(self, rel_path: str) -> Path:
        """库内相对路径 -> 绝对路径。"""
        return self.root / rel_path

    def add_file(self, paper_id: int, kind: str, src: Path | str) -> tuple[str, str]:
        """把外部文件复制进该论文目录。返回 (库内相对路径(POSIX 风格), sha256)。

        文件名 = 原名主干(截断) + 哈希前 8 位，既可读又避免重名与 Windows 路径过长。
        """
        src = Path(src)
        digest = sha256_of(src)
        stem = _BAD_CHARS.sub("_", src.stem).strip(" .")[:40] or "file"
        target_dir = self.papers_dir / str(paper_id) / KIND_DIRS[kind]
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"{stem}_{digest[:8]}{src.suffix.lower()}"
        if not target.exists():
            shutil.copy2(src, target)
        return target.relative_to(self.root).as_posix(), digest

    def remove_file(self, rel_path: str) -> None:
        p = self.abs_path(rel_path)
        if p.exists():
            p.unlink()

    def remove_paper_dir(self, paper_id: int) -> None:
        d = self.papers_dir / str(paper_id)
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)

    def read_text(self, rel_path: str) -> str:
        """读取库内文本文件（翻译 md、卡片 txt），自动处理常见编码。"""
        data = self.abs_path(rel_path).read_bytes()
        for enc in ("utf-8-sig", "gb18030"):
            try:
                return data.decode(enc)
            except UnicodeDecodeError:
                continue
        return data.decode("utf-8", errors="replace")
