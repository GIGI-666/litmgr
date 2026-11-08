"""把仓库内可编辑技能重新生成可分发 ZIP。

【作用】确保 skill/ 中的源码与安装包一致，便于协作开发后重新导入。
【职责】打包完整技能目录，排除 Git/字节码缓存，校验 ZIP 后原子替换旧包。
【依赖】Python 标准库，不需要 ChatGPT 账号或模型 API。
【被谁调用】维护者手动运行 python scripts/package_skill.py。
【扩展点】其他技能可用命令行传入源目录和目标 ZIP，默认处理论文翻译技能。
"""

from __future__ import annotations

import argparse
from pathlib import Path
import tempfile
import zipfile


def package(source: Path, output: Path) -> int:
    """校验源技能并打包到指定 ZIP，返回文件数；拒绝把输出写进技能源码目录。"""
    source, output = source.resolve(), output.resolve()
    if not (source / "SKILL.md").is_file():
        raise ValueError("技能缺少 SKILL.md")
    if output.is_relative_to(source):
        raise ValueError("输出 ZIP 必须放在技能源码目录外")
    files = sorted(p for p in source.rglob("*") if p.is_file()
                   and not {"__pycache__", ".git"}.intersection(p.relative_to(source).parts)
                   and p.suffix != ".pyc")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".skill-package-", dir=output.parent) as temp:
        archive = Path(temp) / "skill.zip"
        with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as z:
            for file in files:
                z.write(file, arcname=(Path(source.name) / file.relative_to(source)).as_posix())
        with zipfile.ZipFile(archive) as z:
            if z.testzip() is not None or len(z.namelist()) != len(files):
                raise ValueError("技能 ZIP 完整性检查失败")
            for file in files:
                name = (Path(source.name) / file.relative_to(source)).as_posix()
                if z.read(name) != file.read_bytes():
                    raise ValueError(f"ZIP 内容不一致：{name}")
        archive.replace(output)
    return len(files)


def main() -> None:
    """处理可选源/目标参数，默认重建仓库自带的论文翻译技能包。"""
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", type=Path, default=root / "skill/paper-translate-package")
    parser.add_argument("--output", type=Path, default=root / "skill/paper-translate-package.zip")
    args = parser.parse_args()
    count = package(args.source, args.output)
    print(f"Packaged {count} files: {args.output.name}")


if __name__ == "__main__":
    main()
