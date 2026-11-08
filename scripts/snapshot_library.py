"""生成可随仓库分享的独立文献库快照。

【作用】不改原库，复制数据库、PDF、翻译、卡片、已有备份及其他库文件。
【职责】用 SQLite 在线备份获得一致数据库，排除锁与日志，检查完整性、外键和文件哈希。
【依赖】仅标准库；数据库结构沿用 storage/migrations，无需启动 GUI 或安装 PySide6。
【被谁调用】维护者准备分享/交接数据时手动运行，不在应用启动流程调用。
【扩展点】新增瞬态文件请补排除规则，新增业务数据仍保存在数据库或文献库中。
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile


def digest(path: Path) -> str:
    """流式计算文件的 SHA-256，适用于较大的论文 PDF。"""
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def backup_database(source: Path, destination: Path) -> None:
    """只读打开来源，通过 SQLite backup 复制已提交数据，兼容正在使用的 WAL 库。"""
    reader = sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True)
    writer = sqlite3.connect(destination)
    try:
        reader.backup(writer)
        if writer.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise ValueError(f"数据库完整性检查失败：{source.name}")
    finally:
        writer.close()
        reader.close()


def snapshot(source: Path, destination: Path, config: Path | None = None) -> dict:
    """创建新的完整快照目录；目标已存在时拒绝覆盖，返回业务数据概况。"""
    source, destination = source.resolve(), destination.resolve()
    if not (source / "db/litmgr.db").is_file():
        raise ValueError("来源不是文献库：缺少 db/litmgr.db")
    if destination.exists():
        raise ValueError("目标目录已存在，请指定新目录；不会覆盖已有文献库")
    if destination.is_relative_to(source) or source.is_relative_to(destination):
        raise ValueError("快照和原库必须是互不包含的独立目录")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".litmgr-snapshot-", dir=destination.parent) as temp:
        stage = Path(temp) / "library"
        (stage / "db").mkdir(parents=True)
        backup_database(source / "db/litmgr.db", stage / "db/litmgr.db")
        for path in sorted(source.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(source)
            if relative.as_posix() == "db/litmgr.db":
                continue
            if path.name == ".litmgr.lock" or path.name.endswith(("-wal", "-shm", "-journal", ".log")):
                continue
            target = stage / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if path.suffix.lower() == ".db":
                backup_database(path, target)
            else:
                shutil.copyfile(path, target)
                if digest(path) != digest(target):
                    raise ValueError(f"文件复制过程中发生变化：{relative}")
        # backup 已将已提交内容写进独立主文件，检查时不创建新的 WAL/SHM 临时文件。
        db = sqlite3.connect((stage / "db/litmgr.db").as_uri() + "?mode=ro&immutable=1", uri=True)
        db.row_factory = sqlite3.Row
        try:
            if db.execute("PRAGMA foreign_key_check").fetchall():
                raise ValueError("快照数据库外键检查失败")
            for file in db.execute("SELECT rel_path, sha256 FROM paper_file"):
                copied = (stage / file["rel_path"]).resolve()
                if not copied.is_relative_to(stage) or not copied.is_file():
                    raise ValueError(f"数据库关联文件不存在或越界：{file['rel_path']}")
                if file["sha256"] and digest(copied) != file["sha256"]:
                    raise ValueError(f"数据库登记的文件哈希与实际内容不符：{file['rel_path']}")
            tables = ("paper", "field_def", "field_group", "field_value", "paper_file", "note",
                      "tag", "collection", "saved_view", "change_log", "pending_content", "reading_history")
            counts = {table: db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in tables}
            kinds = dict(Counter(row[0] for row in db.execute("SELECT kind FROM paper_file")))
            schema = db.execute("PRAGMA user_version").fetchone()[0]
        finally:
            db.close()
        if config:
            settings = json.loads(config.read_text(encoding="utf-8-sig"))
            settings["library_path"], settings["recent_libraries"] = "", []
            (stage / "config.snapshot.json").write_text(
                json.dumps(settings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        files = {p.relative_to(stage).as_posix(): {"bytes": p.stat().st_size, "sha256": digest(p)}
                 for p in sorted(stage.rglob("*")) if p.is_file()}
        report = {"captured_at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
                  "schema_version": schema, "counts": counts, "file_kinds": kinds,
                  "backup_count": len(list((stage / "backups").glob("*.db"))),
                  "total_bytes": sum(info["bytes"] for info in files.values()), "files": files,
                  "note": "数据库由 SQLite 在线备份生成；排除运行锁、WAL/SHM/journal及日志；"
                          "配置保留启动偏好和窗口布局，清空本机文献库绝对路径。"}
        (stage / "snapshot_manifest.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        stage.rename(destination)
    return report


def main() -> None:
    """接收来源、全新目标与可选配置，输出快照计数，失败时返回非零状态。"""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("source", type=Path, help="原文献库文件夹，可在原应用运行时读取已提交数据")
    parser.add_argument("destination", type=Path, help="新的快照目录，不能已存在")
    parser.add_argument("--config", type=Path, help="可选的 AppConfig JSON，导出可移植设置副本")
    args = parser.parse_args()
    report = snapshot(args.source, args.destination, args.config)
    print(json.dumps({key: value for key, value in report.items() if key != "files"},
                     ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
