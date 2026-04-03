#!/usr/bin/env python3
"""Compile Mneme raw evidence into a first-pass compiled memory pack.

Primary input:
- raw/sources.jsonl
- raw/items.jsonl

Legacy fallback:
- direct markdown parsing from MEMORY.md + memory/*.md

The output is a starting point for human/agent review, not final truth.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Any

CATEGORY_RULES = {
    "projects": [
        r"\bproject\b", r"\brepo\b", r"\bbranch\b", r"\bdeploy\b", r"\blive\b",
        r"\bpath\b", r"\bworktree\b", r"\bfrontend\b", r"\bbackend\b", r"\bmap\b",
    ],
    "systems": [
        r"\bhost\b", r"\bserver\b", r"\bssh\b", r"\bgateway\b", r"\bnats\b",
        r"\bmemory\b", r"\bmysql\b", r"\bmqtt\b", r"\bforgejo\b", r"\bapi\b",
    ],
    "decisions": [
        r"\bdecid", r"\bhard rule\b", r"\bdo not\b", r"\bmust\b", r"\bshould\b",
        r"\bprefer\b", r"\brule\b", r"\bchosen\b", r"\blocked\b",
    ],
    "incidents": [
        r"\bincident\b", r"\broot cause\b", r"\boutage\b", r"\bfailed\b", r"\bbroken\b",
        r"\bcompromise\b", r"\bspike\b", r"\bcpu\b", r"\bram\b", r"\bfix\b",
    ],
}

SECRET_PATTERNS = [
    (re.compile(r"ghp_[A-Za-z0-9_]+"), "ghp_[REDACTED]"),
    (re.compile(r"(token\s*[:=]\s*)([^\s,`]+)", re.I), r"\1[REDACTED]"),
    (re.compile(r"(api[_-]?key\s*[:=]\s*)([^\s,`]+)", re.I), r"\1[REDACTED]"),
    (re.compile(r"(pass(word)?\s*[:=]\s*)([^\s,`]+)", re.I), r"\1[REDACTED]"),
    (re.compile(r"(botToken\s*[:=]\s*)([^\s,`]+)", re.I), r"\1[REDACTED]"),
]

IGNORE_MEMORY_FILES = {
    "projects.md",
    "systems.md",
    "decisions.md",
    "incidents.md",
    "timeline.md",
}


@dataclass
class SourceLine:
    file: str
    line_no: int
    text: str
    evidence_id: str | None = None


def redact(text: str) -> str:
    out = text
    for pattern, repl in SECRET_PATTERNS:
        out = pattern.sub(repl, out)
    return out


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def source_files(root: Path) -> list[Path]:
    files: list[Path] = []
    memory_md = root / "MEMORY.md"
    if memory_md.exists():
        files.append(memory_md)
    memory_dir = root / "memory"
    if memory_dir.exists():
        for path in sorted(memory_dir.glob("*.md")):
            if path.name in IGNORE_MEMORY_FILES:
                continue
            if path.name.endswith("-memory-pre-trim.md") or path.name.endswith(".bak"):
                continue
            files.append(path)
    return files


def iter_candidate_lines(path: Path, root: Path) -> Iterable[SourceLine]:
    for i, raw in enumerate(path.read_text(errors="replace").splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#") or line.startswith("-") or line.startswith("*"):
            yield SourceLine(str(path.relative_to(root)), i, redact(line))


def matches_any(text: str, patterns: list[str]) -> bool:
    lower = text.lower()
    return any(re.search(p, lower) for p in patterns)


def collect_legacy(root: Path) -> tuple[dict[str, list[SourceLine]], list[str], list[tuple[str, str, str]]]:
    collected = {k: [] for k in CATEGORY_RULES}
    files = source_files(root)
    sources = [str(p.relative_to(root)) for p in files]
    timeline: list[tuple[str, str, str]] = []
    date_re = re.compile(r"(20\d{2}-\d{2}-\d{2})")
    for path in files:
        rel = str(path.relative_to(root))
        for item in iter_candidate_lines(path, root):
            for category, patterns in CATEGORY_RULES.items():
                if matches_any(item.text, patterns):
                    collected[category].append(item)
        m = date_re.search(rel)
        file_date = m.group(1) if m else "undated"
        for line in path.read_text(errors="replace").splitlines():
            stripped = line.strip()
            if stripped.startswith("## "):
                timeline.append((file_date, redact(stripped[3:]), rel))
    return collected, sources, timeline


def collect_from_raw(raw_dir: Path) -> tuple[dict[str, list[SourceLine]], list[str], list[tuple[str, str, str]]]:
    sources_rows = load_jsonl(raw_dir / "sources.jsonl")
    items_rows = load_jsonl(raw_dir / "items.jsonl")
    if not sources_rows or not items_rows:
        raise FileNotFoundError(f"Missing raw Mneme evidence in {raw_dir}")

    sources = [row.get("workspacePath") or row.get("uri") or row.get("id") for row in sources_rows]
    collected = {k: [] for k in CATEGORY_RULES}
    timeline: list[tuple[str, str, str]] = []
    seen_timeline: set[tuple[str, str, str]] = set()

    for item in items_rows:
        text = redact(item.get("text", "").strip())
        if not text:
            continue
        prov = item.get("provenance", {})
        rel = prov.get("path") or item.get("sourceId") or "unknown"
        line_no = prov.get("lineStart") or 0
        candidate = SourceLine(rel, int(line_no), text, item.get("id"))
        for category, patterns in CATEGORY_RULES.items():
            if matches_any(text, patterns):
                collected[category].append(candidate)
        if item.get("kind") in {"note_section", "memory_line"}:
            heading_path = prov.get("headingPath") or []
            title = None
            if text.startswith("## "):
                title = text[3:].strip()
            elif heading_path:
                title = heading_path[-1]
            if title:
                observed = item.get("observedAt", "")
                date_key = observed[:10] if observed else "undated"
                key = (date_key, title, rel)
                if key not in seen_timeline:
                    seen_timeline.add(key)
                    timeline.append(key)

    timeline.sort()
    return collected, sources, timeline


def unique_lines(items: list[SourceLine], limit: int = 80) -> list[SourceLine]:
    seen: set[str] = set()
    out: list[SourceLine] = []
    for item in items:
        key = item.text.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
        if len(out) >= limit:
            break
    return out


def write_category(path: Path, title: str, items: list[SourceLine], sources: list[str], mode: str) -> None:
    lines = [
        f"# Compiled Memory — {title}",
        "",
        f"> Generated by `scripts/mneme_compile_memory.py` from **{mode}** input. Review before treating as truth.",
        "",
        "## Candidate facts",
    ]
    if items:
        for item in items:
            lines.append(f"- {item.text}  ")
            lines.append(f"  Source: `{item.file}:{item.line_no}`")
            if item.evidence_id:
                lines.append(f"  Evidence: `{item.evidence_id}`")
    else:
        lines.append("- No candidate facts found in this pass.")
    lines.extend([
        "",
        "## Sources",
        *[f"- `{s}`" for s in sources],
        "",
    ])
    path.write_text("\n".join(lines))


def build_timeline(out_path: Path, entries: list[tuple[str, str, str]], sources: list[str], mode: str) -> None:
    lines = [
        "# Compiled Memory — Timeline",
        "",
        f"> Generated by `scripts/mneme_compile_memory.py` from **{mode}** input. Review before treating as truth.",
        "",
    ]
    if entries:
        current = None
        for date, title, rel in entries[:200]:
            if date != current:
                lines.append(f"## {date}")
                current = date
            lines.append(f"- {title}  ")
            lines.append(f"  Source: `{rel}`")
    else:
        lines.append("- No timeline entries found.")
    lines.extend(["", "## Sources", *[f"- `{s}`" for s in sources], ""])
    out_path.write_text("\n".join(lines))


def build_report(out_dir: Path, sources: list[str], collected: dict[str, list[SourceLine]], mode: str, raw_dir: str | None) -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# Mneme Compile Report",
        "",
        f"Generated: {now}",
        f"Mode: {mode}",
    ]
    if raw_dir:
        lines.append(f"Raw input: `{raw_dir}`")
    lines.extend([
        "",
        "## Inputs",
        *[f"- `{s}`" for s in sources],
        "",
        "## Candidate counts",
    ])
    for category, items in collected.items():
        lines.append(f"- {category}: {len(unique_lines(items))}")
    lines.extend([
        "",
        "## Notes",
        "- This pass is deterministic and conservative.",
        "- It preserves source references instead of pretending to know final truth.",
        "- Review, trim, and promote before merging into long-term memory.",
        "",
    ])
    (out_dir / "report.md").write_text("\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a first-pass compiled memory pack.")
    parser.add_argument("--root", default=".", help="Workspace root containing MEMORY.md and memory/*.md")
    parser.add_argument("--out", default="compiled", help="Output directory for compiled files")
    parser.add_argument("--raw", default=None, help="Directory containing raw/sources.jsonl and raw/items.jsonl")
    parser.add_argument("--legacy-direct", action="store_true", help="Ignore raw evidence and parse markdown directly")
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    out_dir = Path(args.out).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    mode = "legacy-direct"
    raw_dir = None
    if args.legacy_direct:
        collected, sources, timeline = collect_legacy(root)
    else:
        raw_candidate = Path(args.raw).expanduser().resolve() if args.raw else (root / "raw")
        try:
            collected, sources, timeline = collect_from_raw(raw_candidate)
            mode = "raw-evidence"
            raw_dir = str(raw_candidate)
        except FileNotFoundError:
            collected, sources, timeline = collect_legacy(root)

    write_category(out_dir / "projects.md", "Projects", unique_lines(collected["projects"]), sources, mode)
    write_category(out_dir / "systems.md", "Systems", unique_lines(collected["systems"]), sources, mode)
    write_category(out_dir / "decisions.md", "Decisions", unique_lines(collected["decisions"]), sources, mode)
    write_category(out_dir / "incidents.md", "Incidents", unique_lines(collected["incidents"]), sources, mode)
    build_timeline(out_dir / "timeline.md", timeline, sources, mode)
    build_report(out_dir, sources, collected, mode, raw_dir)

    print(f"Compiled memory pack written to {out_dir} (mode={mode})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
