"""文献库文件夹管理。

【作用】管理“文献库”这个文件夹的目录结构，负责把外部文件复制进库、解析库内路径。
【文献库结构】
    <文献库>/
        db/litmgr.db          数据库
        papers/<paper_id>/    每篇论文一个目录
            card/ pdf/ translation/ attachments/
        backups/              数据库自动备份
    整个文件夹复制走即可完成备份/迁移（数据库里只存相对路径）。
【依赖】仅标准库；core.models（文件种类常量）、core.textutil。
【被谁调用】services.app_context（创建）、import_service / paper_service（复制、删除文件）、
    ui（取绝对路径打开文件）。
【扩展点】新增文件种类时在 KIND_DIRS 增加映射。
"""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from ..core.models import KIND_ATTACHMENT, KIND_CARD, KIND_PDF, KIND_TRANSLATION
from ..core.textutil import decode_text, safe_filename

KIND_DIRS = {
    KIND_CARD: "card",
    KIND_PDF: "pdf",
    KIND_TRANSLATION: "translation",
    KIND_ATTACHMENT: "attachments",
}


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
        stem = safe_filename(src.stem, limit=40, default="file")
        target_dir = self.papers_dir / str(paper_id) / KIND_DIRS[kind]
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"{stem}_{digest[:8]}{src.suffix.lower()}"
        # 目标已存在时只有大小一致才复用；否则可能是上次复制中断留下的半截文件，重新复制
        if not target.exists() or target.stat().st_size != src.stat().st_size:
            tmp = target.with_name(target.name + ".part")
            shutil.copy2(src, tmp)
            tmp.replace(target)    # 先复制到临时名再改名：中断时不会留下看似完整的半截文件
        return target.relative_to(self.root).as_posix(), digest

    def remove_file(self, rel_path: str) -> None:
        p = self.abs_path(rel_path)
        if p.exists():
            p.unlink()

    def iter_library_files(self):
        """遍历 papers/ 下的所有文件，产出 (绝对路径, 库内相对路径)。"""
        for p in self.papers_dir.rglob("*"):
            if p.is_file():
                yield p, p.relative_to(self.root).as_posix()

    def prune_empty_dirs(self) -> None:
        """删除 papers/ 下已经空了的子目录（自底向上）。"""
        for d in sorted((x for x in self.papers_dir.rglob("*") if x.is_dir()),
                        key=lambda x: len(x.parts), reverse=True):
            try:
                d.rmdir()
            except OSError:
                pass    # 非空就保留

    def remove_paper_dir(self, paper_id: int) -> None:
        d = self.papers_dir / str(paper_id)
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)

    def read_text(self, rel_path: str) -> str:
        """读取库内文本文件（翻译 md、卡片 txt），自动处理常见编码。"""
        return decode_text(self.abs_path(rel_path).read_bytes())
