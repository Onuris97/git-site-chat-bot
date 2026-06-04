# -*- coding: utf-8 -*-
"""Audit 1C project structure and BSL export dependencies."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


KW_PROC = "\u041f\u0440\u043e\u0446\u0435\u0434\u0443\u0440\u0430"
KW_FUNC = "\u0424\u0443\u043d\u043a\u0446\u0438\u044f"
KW_CLASS = "\u041a\u043b\u0430\u0441\u0441"
KW_EXPORT = "\u042d\u043a\u0441\u043f\u043e\u0440\u0442"

RUS_ID = r"[A-Za-z\u0400-\u04FF_][A-Za-z\u0400-\u04FF_0-9]*"

RE_DEF = re.compile(
    rf"(?im)^\s*(?:&[^\r\n]+\s*)*(?P<kind>{re.escape(KW_PROC)}|{re.escape(KW_FUNC)})\s+(?P<name>{RUS_ID})\s*\("
)
RE_CLASS = re.compile(rf"(?im)^\s*{re.escape(KW_CLASS)}\s+(?P<name>{RUS_ID})\b")

ENCODINGS = ("utf-8-sig", "utf-8", "cp1251")


@dataclass(frozen=True)
class Routine:
    kind: str
    name: str
    is_export: bool


@dataclass(frozen=True)
class ExportRoutine:
    module: str | None
    file: str
    kind: str
    name: str


def read_text_auto(path: Path) -> str:
    raw = path.read_bytes()
    for enc in ENCODINGS:
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def tree_dirs_first(root: Path, max_depth: int = 4) -> list[str]:
    out: list[str] = [str(root)]

    def walk(cur: Path, prefix: str, depth: int) -> None:
        if depth == 0:
            return
        entries = sorted(cur.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        for idx, entry in enumerate(entries):
            is_last = idx == len(entries) - 1
            branch = "`-- " if is_last else "|-- "
            out.append(prefix + branch + entry.name)
            if entry.is_dir():
                ext = "    " if is_last else "|   "
                walk(entry, prefix + ext, depth - 1)

    walk(root, "", max_depth)
    return out


def extract_header_with_parens(text: str, start_idx: int) -> str:
    start_paren = text.find("(", start_idx)
    if start_paren < 0:
        return ""
    depth = 0
    i = start_paren
    while i < len(text):
        ch = text[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return text[start_idx : min(len(text), i + 160)]
        i += 1
    return text[start_idx : min(len(text), start_idx + 160)]


def parse_routines(text: str) -> tuple[list[Routine], list[str]]:
    routines: list[Routine] = []
    for m in RE_DEF.finditer(text):
        head = extract_header_with_parens(text, m.start())
        is_export = re.search(rf"(?i)\b{re.escape(KW_EXPORT)}\b", head) is not None
        routines.append(Routine(kind=m.group("kind"), name=m.group("name"), is_export=is_export))
    classes = [m.group("name") for m in RE_CLASS.finditer(text)]
    return routines, classes


def module_name_for_path(rel_posix: str) -> str | None:
    parts = rel_posix.split("/")
    if (
        len(parts) >= 4
        and parts[0] == "src"
        and parts[1] == "CommonModules"
        and parts[-2] == "Ext"
        and parts[-1] == "Module.bsl"
    ):
        return parts[2]
    return None


def collect_dependencies(content: str, known_modules: set[str], skip_module: str | None) -> list[str]:
    deps: set[str] = set()
    for mod in known_modules:
        if mod == skip_module:
            continue
        if re.search(r"(?i)\b" + re.escape(mod) + r"\s*\.", content):
            deps.add(mod)
    return sorted(deps, key=str.lower)


def to_md_list(values: list[str]) -> str:
    return ", ".join(values) if values else "-"


def build_report(repo_root: Path) -> tuple[Path, int, int, int]:
    src_root = repo_root / "src"
    out_file = repo_root / "docs" / "grace_audit.md"

    bsl_files = sorted(src_root.rglob("*.bsl"))
    texts: dict[str, str] = {}
    rows: list[dict] = []
    exports: list[ExportRoutine] = []

    known_modules: set[str] = set()
    for fp in bsl_files:
        rel = fp.relative_to(repo_root).as_posix()
        mod = module_name_for_path(rel)
        if mod:
            known_modules.add(mod)

    for fp in bsl_files:
        rel = fp.relative_to(repo_root).as_posix()
        text = read_text_auto(fp)
        texts[rel] = text
        line_count = len(text.splitlines())
        routines, classes = parse_routines(text)
        public_routines = [f"{r.kind} {r.name}" for r in routines if r.is_export]
        module_name = module_name_for_path(rel)

        for r in routines:
            if r.is_export:
                exports.append(ExportRoutine(module=module_name, file=rel, kind=r.kind, name=r.name))

        rows.append(
            {
                "file": rel,
                "lines": line_count,
                "public_routines": sorted(public_routines, key=str.lower),
                "classes": sorted(classes, key=str.lower),
                "depends_on": collect_dependencies(text, known_modules, module_name),
            }
        )

    callers_by_export: dict[tuple[str | None, str, str], set[str]] = defaultdict(set)
    for exp in exports:
        if exp.module:
            pattern = re.compile(
                r"(?i)\b" + re.escape(exp.module) + r"\s*\.\s*" + re.escape(exp.name) + r"\s*\("
            )
        else:
            # Fallback for non-common modules: unqualified call search by name.
            pattern = re.compile(r"(?i)\b" + re.escape(exp.name) + r"\s*\(")
        for row in rows:
            if row["file"] == exp.file:
                continue
            if pattern.search(texts[row["file"]]):
                callers_by_export[(exp.module, exp.file, exp.name)].add(row["file"])

    unused = [exp for exp in exports if not callers_by_export.get((exp.module, exp.file, exp.name))]

    h1 = "# GRACE Audit\n\n"
    p0 = "Report generated by `tools/_grace_audit_cf.py`.\n\n"
    h2 = "## 1. Source tree (`src`)\n\n"
    h3 = "## 2. `.bsl` files summary\n\n"
    h4 = "## 3. Dependencies and exports\n\n"
    p1 = "Table format: `[file] -> [depends on] -> [exports]`.\n\n"
    h5 = "## 4. Export call map (who depends on whom)\n\n"
    h6 = "## 5. Exports not used in other modules\n\n"

    md: list[str] = [h1, p0, h2, "```text\n", "\n".join(tree_dirs_first(src_root, 4)), "\n```\n\n"]
    md.append(h3)
    md.append("| File | Lines | Public functions/procedures | Public classes |\n")
    md.append("|---|---:|---|---|\n")
    for row in rows:
        md.append(
            f"| `{row['file']}` | {row['lines']} | {to_md_list(row['public_routines'])} | {to_md_list(row['classes'])} |\n"
        )
    md.append("\n")

    md.append(h4)
    md.append(p1)
    md.append("| File | Depends on | Exports |\n")
    md.append("|---|---|---|\n")
    for row in rows:
        md.append(
            f"| `{row['file']}` | {to_md_list(row['depends_on'])} | {to_md_list(row['public_routines'])} |\n"
        )
    md.append("\n")

    md.append(h5)
    md.append("| Export (module.name) | Module file | Used in modules |\n")
    md.append("|---|---|---|\n")
    for exp in sorted(exports, key=lambda x: ((x.module or x.file).lower(), x.name.lower())):
        callers = sorted(callers_by_export.get((exp.module, exp.file, exp.name), set()), key=str.lower)
        export_key = f"{exp.module}.{exp.name}" if exp.module else f"{exp.file}::{exp.name}"
        md.append(f"| `{export_key}` | `{exp.file}` | {to_md_list(callers)} |\n")
    md.append("\n")

    md.append(h6)
    if unused:
        md.append("| Export (module.name) | File |\n")
        md.append("|---|---|\n")
        for exp in sorted(unused, key=lambda x: ((x.module or x.file).lower(), x.name.lower())):
            export_key = f"{exp.module}.{exp.name}" if exp.module else f"{exp.file}::{exp.name}"
            md.append(f"| `{export_key}` | `{exp.file}` |\n")
    else:
        md.append("No unused exports found.\n")

    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text("".join(md), encoding="utf-8")
    return out_file, len(bsl_files), len(exports), len(unused)


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    out_file, bsl_count, exports_count, unused_count = build_report(repo_root)
    print(f"Written: {out_file}")
    print(f"BSL files: {bsl_count}")
    print(f"Exports: {exports_count}")
    print(f"Unused exports: {unused_count}")


if __name__ == "__main__":
    main()
