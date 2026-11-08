"""论文翻译文件包的准备、进度登记、结构校验与打包工具。

【作用】快照原 PDF 与当前 TXT 模板，记录模型实际译出的分段，生成卡片和成品目录/ZIP。
【职责】验证字段集合、页码覆盖、文件哈希与输出集合；不执行翻译、不证明语义完整。
【依赖】仅 Python 3.10+ 标准库，可在桌面本机或文件执行环境运行。
【被谁调用】paper-translate-package 技能；所有路径由当次调用提供。
【扩展点】新模板格式在 read_fields 扩展；新导出文件在 finalize 扩展，勿改输入 PDF。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path


def sha256(path: Path) -> str:
    """分块计算原始字节哈希，避免一次读入大 PDF。"""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_text(path: Path) -> str:
    """兼容 UTF-8 BOM、UTF-16 BOM 及常见 Windows 中文 TXT 编码。"""
    raw = path.read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16")
    for encoding in ("utf-8-sig", "gb18030"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            pass
    raise ValueError(f"无法可靠解码文件：{path}")


def read_fields(path: Path) -> list[str]:
    """从每行字段模板取字段名，忽略明确组标题，拒绝歧义重名。"""
    fields, seen = [], set()
    for raw in read_text(path).splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or re.fullmatch(r"【[^】]+】|\[[^\]]+\]", line):
            continue
        line = re.sub(r"^(?:[（(]\s*\d+\s*[）)]|\d+[.)、])\s*", "", line)
        name = re.split(r"[：:]", line, maxsplit=1)[0].strip()
        key = re.sub(r"\s+", "", name).casefold()
        if not key or key in seen:
            raise ValueError(f"模板含空字段或重复字段：{name!r}")
        seen.add(key)
        fields.append(name)
    if not fields:
        raise ValueError("模板没有可识别字段，请提供每行一个字段名的 TXT")
    return fields


def safe_stem(value: str) -> str:
    """清理 Windows 文件名并避免被 litmgr 把前缀自身误识别为后缀。"""
    value = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "_", value).strip(" .")[:100].rstrip(" .")
    if not value:
        raise ValueError("文件名前缀不能为空")
    if re.fullmatch(r"CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9]", value.split(".")[0], re.I):
        value = "_" + value
    if value.endswith(("论文详细内容", "论文卡片", "补充材料", "附录", "翻译")):
        value += "_paper"
    # 纯编号会被导入器剥离成空标题，要求标题前缀可独立识别。
    if not re.sub(r"(?:\d{4}\.\d{4,5}|\d{4})(?:v\d+)?$", "", value).strip(" _-"):
        value = "论文_" + value
    return value


def write_text(path: Path, text: str) -> None:
    """以 UTF-8 原始文本保存，避免 shell 转义损坏 LaTeX。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def write_json(path: Path, value) -> None:
    """工作状态原子写入，续作时不会读取半个 JSON。"""
    temp = path.with_name(path.name + ".tmp")
    write_text(temp, json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temp.replace(path)


def no_duplicate_keys(pairs):
    """拒绝 JSON 重复键，防止同一字段后值静默覆盖前值。"""
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"JSON 含重复键：{key}")
        out[key] = value
    return out


def load_json(path: Path):
    """读取 UTF-8 JSON，并检查重复键。"""
    return json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=no_duplicate_keys)


def load_work(path: str) -> tuple[Path, dict]:
    """加载本工具建立的工作目录，检查清单版本与前缀。"""
    work = Path(path).resolve()
    data = load_json(work / "manifest.json")
    if data.get("version") != 1 or safe_stem(data["stem"]) != data["stem"]:
        raise ValueError("不支持的工作清单版本或无效文件名前缀")
    return work, data


def local_file(work: Path, relative: str) -> Path:
    """工作文件须留在工作目录内，不允许清单中的相对路径越界。"""
    path = (work / relative).resolve()
    if not path.is_relative_to(work):
        raise ValueError(f"工作文件路径越界：{relative}")
    return path


def init(args) -> dict:
    """快照必需输入和可选补充材料；只建工作目录，不发布半成品。"""
    if bool(args.supplement) != bool(args.supplement_pages):
        raise ValueError("补充材料文件与其真实页数必须一起提供；没有则两者均省略")
    fields = read_fields(Path(args.template))
    root = Path(args.output_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    stem = safe_stem(args.stem)
    work = root / f".{stem}.work"
    if any(p.exists() for p in (work, root / stem, root / f"{stem}.zip")):
        raise ValueError("同名前缀已有工作目录或成品，请续作现有工作或换一个前缀；不会覆盖")
    data = {"version": 1, "stem": stem, "title_zh": args.title_zh.strip(),
            "title_en": (args.title_en or "").strip(), "output_root": str(root),
            "fields": fields, "sources": {}, "parts": [], "card": None}
    if not data["title_zh"]:
        raise ValueError("中文标题不能为空")
    with tempfile.TemporaryDirectory(prefix=".paper-init-", dir=root) as temporary:
        stage = Path(temporary) / "job"
        (stage / "sources").mkdir(parents=True)
        template = Path(args.template).resolve()
        shutil.copyfile(template, stage / "template.txt")
        data["template_sha256"] = sha256(stage / "template.txt")
        data["template_original"] = str(template)
        if read_fields(stage / "template.txt") != fields or sha256(template) != data["template_sha256"]:
            raise ValueError("模板在读取过程中发生变化，请重新准备")
        sources = [("main", args.main, args.main_pages)]
        if args.supplement:
            sources.append(("supplement", args.supplement, args.supplement_pages))
        for kind, filename, pages in sources:
            source = Path(filename).resolve()
            with source.open("rb") as stream:
                if b"%PDF-" not in stream.read(1024):
                    raise ValueError(f"文件缺少 PDF 头，请确认真实 PDF：{source}")
            relative = f"sources/{kind}.pdf"
            copied = stage / relative
            shutil.copyfile(source, copied)
            digest = sha256(source)
            if sha256(copied) != digest:
                raise ValueError(f"PDF 复制校验失败或输入正在变化：{source}")
            data["sources"][kind] = {"original": str(source), "path": relative,
                                     "sha256": digest, "pages": pages}
        write_json(stage / "manifest.json", data)
        stage.rename(work)
    return {"work": str(work), "fields": fields, "sources": data["sources"]}


def check_part(text: str) -> None:
    """拒绝空译文、包住整个文件的 Markdown 围栏和明显未译占位行。"""
    if not text.strip():
        raise ValueError("译文段落不能为空")
    if re.match(r"^\s*```(?:markdown|md)\s*\n", text, re.I):
        raise ValueError("请写原始 Markdown 文件，不要给整个译文套 Markdown 代码块")
    if re.search(r"(?m)^\s*(?:\[待翻译\]|【待翻译】|TODO|参考文献略|正文略|以下省略)\s*$", text):
        raise ValueError("译文段落含未完成占位行")


def add_part(args) -> dict:
    """登记一段已译文字的来源页码；同一 ID 可明确修订而不会重复追加。"""
    work, data = load_work(args.work)
    source = data["sources"].get(args.source)
    if source is None or not 1 <= args.start <= args.end <= source["pages"]:
        raise ValueError("来源不存在或页码超出真实 PDF 范围")
    part_id = args.id or f"p{len(data['parts']) + 1:04d}"
    if not re.fullmatch(r"p\d{4,}", part_id):
        raise ValueError("分段 ID 必须形如 p0001")
    prior = next((p for p in data["parts"] if p["id"] == part_id), None)
    if args.id and prior is None:
        raise ValueError("修订 ID 不存在；登记新段落请省略 --id")
    text = read_text(Path(args.file)).strip() + "\n"
    check_part(text)
    relative = f"parts/{part_id}.md"
    write_text(work / relative, text)
    part = {"id": part_id, "source": args.source, "start": args.start, "end": args.end,
            "path": relative, "sha256": sha256(work / relative)}
    if prior is None:
        data["parts"].append(part)
    else:
        data["parts"][data["parts"].index(prior)] = part
    write_json(work / "manifest.json", data)
    return part


def render_card(fields: list[str], values: dict) -> str:
    """严格按模板输出带编号的卡片，续行用项目符号避免误判成字段。"""
    if not isinstance(values, dict) or set(values) != set(fields):
        missing = [f for f in fields if not isinstance(values, dict) or f not in values]
        extra = [f for f in values if f not in fields] if isinstance(values, dict) else []
        raise ValueError(f"卡片字段必须与模板一致；缺失={missing}，多余={extra}")
    blocks = []
    for index, field in enumerate(fields, 1):
        value = values[field]
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"字段未填写：{field}；缺证据时请明确写原文未说明/不适用")
        lines = value.strip().splitlines()
        block = f"（{index}）{field}：{lines[0]}"
        for line in lines[1:]:
            block += "\n" + ((line if line.startswith("- ") else "- " + line) if line.strip() else "")
        blocks.append(block)
    return "\n\n".join(blocks) + "\n"


def write_card(args) -> dict:
    """由模型填写的 JSON 生成卡片，拒绝旧字段、多余字段和空值。"""
    work, data = load_work(args.work)
    values = load_json(Path(args.values_json))
    card = render_card(data["fields"], values)
    write_json(work / "card-values.json", values)
    write_text(work / "card.txt", card)
    data["card"] = {"path": "card.txt", "sha256": sha256(work / "card.txt"),
                    "values": "card-values.json"}
    write_json(work / "manifest.json", data)
    return {"card": str(work / "card.txt"), "field_count": len(data["fields"])}


def status_data(work: Path, data: dict) -> dict:
    """汇总页码覆盖缺口；此结果只是登记统计，不证明实际全文已翻译。"""
    sources = {}
    for kind, source in data["sources"].items():
        covered = set()
        for part in data["parts"]:
            if part["source"] == kind:
                covered.update(range(part["start"], part["end"] + 1))
        sources[kind] = {"pages": source["pages"], "registered_pages": len(covered),
                         "missing_pages": sorted(set(range(1, source["pages"] + 1)) - covered)}
    return {"work": str(work), "sources": sources, "parts": data["parts"],
            "fields": data["fields"], "card_written": data["card"] is not None,
            "notice": "登记覆盖不等于语义完整；交付前仍须依据 PDF 审阅全文。"}


def status(args) -> dict:
    """提供供当前会话或续作使用的工作状态。"""
    return status_data(*load_work(args.work))


def validated(work: Path, data: dict) -> dict:
    """检查来源及段落哈希、页码覆盖、当前模板和卡片字段的一致性。"""
    template = work / "template.txt"
    if sha256(template) != data["template_sha256"] or read_fields(template) != data["fields"]:
        raise ValueError("工作模板已改变；新模板应建立新工作，避免前后字段混用")
    for source in data["sources"].values():
        if source["pages"] < 1 or sha256(local_file(work, source["path"])) != source["sha256"]:
            raise ValueError("源 PDF 快照哈希或页数无效")
    identifiers = set()
    for part in data["parts"]:
        if part["id"] in identifiers:
            raise ValueError("分段 ID 重复")
        identifiers.add(part["id"])
        source = data["sources"].get(part["source"])
        if source is None or not 1 <= part["start"] <= part["end"] <= source["pages"]:
            raise ValueError("分段来源或页码无效")
        path = local_file(work, part["path"])
        if sha256(path) != part["sha256"]:
            raise ValueError(f"分段 {part['id']} 已修改，请用 add-part --id 重新登记")
        check_part(read_text(path))
    report = status_data(work, data)
    missing = {kind: s["missing_pages"] for kind, s in report["sources"].items() if s["missing_pages"]}
    if missing:
        raise ValueError(f"仍有未登记翻译的源页：{missing}；不能交付完整包")
    if not data["card"]:
        raise ValueError("尚未生成填好的卡片")
    card = data["card"]
    card_path = local_file(work, card["path"])
    expected = render_card(data["fields"], load_json(local_file(work, card["values"])))
    if sha256(card_path) != card["sha256"] or read_text(card_path) != expected:
        raise ValueError("卡片与已填写字段不一致，请使用 write-card 重新生成")
    return report


def validate(args) -> dict:
    """返回结构检查结果；完整翻译还需人工审阅。"""
    work, data = load_work(args.work)
    return {"structural_checks_passed": True, **validated(work, data)}


def finalize(args) -> dict:
    """审阅后生成唯一成品目录及 ZIP；输入 PDF 只做原字节复制。"""
    if not args.reviewed:
        raise ValueError("请先实际核对翻译、公式、表格、参考文献和卡片，再声明 --reviewed")
    work, data = load_work(args.work)
    validated(work, data)
    root, stem = Path(data["output_root"]), data["stem"]
    target, archive = root / stem, root / f"{stem}.zip"
    if target.exists() or archive.exists():
        raise ValueError("成品目录或 ZIP 已存在，不会覆盖")
    title = "# " + data["title_zh"] + "\n\n"
    if data["title_en"]:
        title += data["title_en"] + "\n\n"
    document = title
    for kind, heading in (("main", "论文正文"), ("supplement", "补充材料")):
        if kind not in data["sources"]:
            continue
        # 同页可拆成多个段；起始页相同按登记顺序拼接，不用文件名的字典序猜顺序。
        parts = sorted((p for p in data["parts"] if p["source"] == kind), key=lambda p: p["start"])
        document += f"## {heading}\n\n"
        document += "\n\n".join(read_text(local_file(work, p["path"])).strip() for p in parts) + "\n\n"
    with tempfile.TemporaryDirectory(prefix=".paper-final-", dir=root) as temporary:
        stage = Path(temporary)
        folder = stage / stem
        folder.mkdir()
        names = []
        for kind, source in data["sources"].items():
            name = stem + ("补充材料" if kind == "supplement" else "") + ".pdf"
            copied = folder / name
            shutil.copyfile(local_file(work, source["path"]), copied)
            if sha256(copied) != source["sha256"]:
                raise ValueError("最终 PDF 副本校验失败")
            names.append(name)
        translation_name, card_name = f"{stem}翻译.md", f"{stem}论文卡片.txt"
        write_text(folder / translation_name, document.rstrip() + "\n")
        write_text(folder / card_name, read_text(local_file(work, data["card"]["path"])))
        names.extend((translation_name, card_name))
        packed = stage / "package.zip"
        with zipfile.ZipFile(packed, "x", compression=zipfile.ZIP_DEFLATED) as z:
            for name in sorted(names):
                z.write(folder / name, arcname=f"{stem}/{name}")
        with zipfile.ZipFile(packed) as z:
            if z.testzip() is not None or set(z.namelist()) != {f"{stem}/{name}" for name in names}:
                raise ValueError("ZIP 完整性或文件集合不匹配")
        folder.rename(target)
        packed.rename(archive)
    return {"folder": str(target), "zip": str(archive), "files": names,
            "field_count": len(data["fields"]), "supplement": "supplement" in data["sources"]}


def positive_int(value: str) -> int:
    """物理页码必须是正整数。"""
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("页码/页数必须大于 0")
    return number


def main() -> int:
    """命令行入口，成功返回 JSON，校验失败返回非零状态。"""
    # Windows 控制台默认编码可能无法输出新模板里的特殊字符；统一机器可读输出编码。
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    p = commands.add_parser("init", help="快照 PDF 与当前卡片模板，建立独立工作目录")
    p.add_argument("--main", required=True)
    p.add_argument("--main-pages", type=positive_int, required=True)
    p.add_argument("--supplement")
    p.add_argument("--supplement-pages", type=positive_int)
    p.add_argument("--template", required=True)
    p.add_argument("--title-zh", required=True)
    p.add_argument("--title-en", default="")
    p.add_argument("--stem", required=True)
    p.add_argument("--output-root", required=True)
    p.set_defaults(handler=init)
    p = commands.add_parser("add-part", help="登记或修订一段真实翻译的源页码与内容")
    p.add_argument("--work", required=True)
    p.add_argument("--source", choices=("main", "supplement"), required=True)
    p.add_argument("--start", type=positive_int, required=True)
    p.add_argument("--end", type=positive_int, required=True)
    p.add_argument("--file", required=True)
    p.add_argument("--id", help="仅修订已有 ID 时提供，例如 p0001")
    p.set_defaults(handler=add_part)
    p = commands.add_parser("write-card", help="按当前模板严格生成填好的卡片 TXT")
    p.add_argument("--work", required=True)
    p.add_argument("--values-json", required=True)
    p.set_defaults(handler=write_card)
    for command, handler in (("status", status), ("validate", validate), ("finalize", finalize)):
        p = commands.add_parser(command)
        p.add_argument("--work", required=True)
        if command == "finalize":
            p.add_argument("--reviewed", action="store_true", help="已经依据 PDF 实际审阅全部内容")
        p.set_defaults(handler=handler)
    args = parser.parse_args()
    try:
        result = args.handler(args)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
