#!/usr/bin/env python3
"""Mneme v1 ingest pipeline for OpenClaw memory files.

Targets:
- MEMORY.md
- memory/*.md

Outputs:
- raw/sources.jsonl
- raw/items.jsonl
- raw/report.json

This is intentionally deterministic and boring.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

IGNORE_MEMORY_FILES = {
    "projects.md",
    "systems.md",
    "decisions.md",
    "incidents.md",
    "timeline.md",
}

SECRET_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"github_pat_[A-Za-z0-9_]+"), "github_pat_[REDACTED]"),
    (re.compile(r"ghp_[A-Za-z0-9_]+"), "ghp_[REDACTED]"),
    (re.compile(r"glpat-[A-Za-z0-9_\-]+"), "glpat-[REDACTED]"),
    (re.compile(r"(?i)(bearer\s+)([A-Za-z0-9._\-]+)"), r"\1[REDACTED]"),
    (re.compile(r'''(?i)(api[_ -]?key\s*[:=]\s*["'`]?)(?!__OPENCLAW_REDACTED__)([^\s"'`,]+)'''), r"\1[REDACTED]"),
    (re.compile(r'''(?i)(gateway\s+token\s*[:=]\s*["'`]?)(?!__OPENCLAW_REDACTED__)([^\s"'`,]+)'''), r"\1[REDACTED]"),
    (re.compile(r'''(?i)(token\s*[:=]\s*["'`]?)(?!__OPENCLAW_REDACTED__)([^\s"'`,]+)'''), r"\1[REDACTED]"),
    (re.compile(r'''(?i)(pass(word)?\s*[:=]\s*["'`]?)(?!<see\s)([^\s"'`,]+)'''), r"\1[REDACTED]"),
    (re.compile(r'''(?i)(creds?\s*[:=]\s*["'`]?)([^\n`]*?/[^\n`]+)'''), r"\1[REDACTED]"),
    (re.compile(r'''(?i)(rdp\s*:\s*["'`]?)([^\n`]*?/[^\n`]+)'''), r"\1[REDACTED]"),
    (re.compile(r"mysql://[^\s)]+"), "mysql://[REDACTED]"),
    (re.compile(r"postgres(ql)?://[^\s)]+"), "postgres://[REDACTED]"),
]

DATE_RE = re.compile(r"(20\d{2}-\d{2}-\d{2})")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def source_files(root: Path) -> list[Path]:
    files: list[Path] = []
    memory_md = root / "MEMORY.md"
    if memory_md.exists():
        files.append(memory_md)
    memdir = root / "memory"
    if memdir.exists():
        for path in sorted(memdir.glob("*.md")):
            if path.name in IGNORE_MEMORY_FILES:
                continue
            if path.name.endswith(".bak"):
                continue
            files.append(path)
    return files


def redact(text: str) -> tuple[str, bool]:
    out = text
    changed = False
    for pattern, repl in SECRET_PATTERNS:
        new = pattern.sub(repl, out)
        if new != out:
            changed = True
            out = new
    return out, changed


def source_type(path: Path) -> str:
    if path.name == "MEMORY.md":
        return "memory_file"
    return "daily_note"


def observed_at(path: Path) -> str | None:
    m = DATE_RE.search(path.name)
    if not m:
        return None
    return f"{m.group(1)}T00:00:00Z"


def build_source(root: Path, path: Path, captured_at: str) -> dict:
    rel = str(path.relative_to(root))
    text = path.read_text(errors="replace")
    digest = sha256_text(text)
    return {
        "id": f"src:{source_type(path)}:{rel}:sha256:{digest[:12]}",
        "sourceType": source_type(path),
        "uri": path.resolve().as_uri(),
        "workspacePath": rel,
        "title": path.name,
        "capturedAt": captured_at,
        "contentHash": f"sha256:{digest}",
        "mimeType": "text/markdown",
    }


def iter_memory_lines(path: Path) -> Iterable[tuple[int, str]]:
    for i, raw in enumerate(path.read_text(errors="replace").splitlines(), start=1):
        line = raw.rstrip()
        if line.strip():
            yield i, line


def item_id(source_id: str, kind: str, line_start: int, line_end: int, text: str) -> str:
    digest = sha256_text(text)
    return f"evi:{kind}:{source_id.split(':', 3)[2]}:{line_start}-{line_end}:sha256:{digest[:12]}"


def heading_path_from_lines(lines: list[tuple[int, str]], current_index: int) -> list[str]:
    path: list[tuple[int, str]] = []
    for i, line in lines:
        if i >= current_index:
            break
        stripped = line.strip()
        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip('#'))
            title = stripped[level:].strip()
            path = [x for x in path if x[0] < level]
            path.append((level, title))
    return [title for _level, title in path]


def build_items(root: Path, path: Path, source: dict, captured_at: str) -> list[dict]:
    rel = str(path.relative_to(root))
    obs = observed_at(path)
    lines = list(iter_memory_lines(path))
    items: list[dict] = []

    # line-based evidence for bullets and headings
    for i, line in lines:
        stripped = line.strip()
        if not (stripped.startswith("#") or stripped.startswith("-") or stripped.startswith("*")):
            continue
        text, redacted = redact(stripped)
        kind = "memory_line" if path.name == "MEMORY.md" else ("note_bullet" if stripped.startswith(("-", "*")) else "note_section")
        item = {
            "id": item_id(source["id"], kind, i, i, text),
            "sourceId": source["id"],
            "kind": kind,
            "text": text,
            "capturedAt": captured_at,
            "provenance": {
                "path": rel,
                "locatorType": "line_range",
                "lineStart": i,
                "lineEnd": i,
                "headingPath": heading_path_from_lines(lines, i),
            },
            "contentHash": f"sha256:{sha256_text(text)}",
            "secretRedacted": redacted,
        }
        if obs:
            item["observedAt"] = obs
        items.append(item)

    # paragraph/section evidence from markdown sections
    section_lines: list[tuple[int, str]] = []
    current_heading = None
    for i, line in lines + [(10**9, "# END")]:
        stripped = line.strip()
        if stripped.startswith("#"):
            if current_heading and section_lines:
                line_start = section_lines[0][0]
                line_end = section_lines[-1][0]
                section_text = "\n".join(x[1].strip() for x in section_lines if x[1].strip())
                text, redacted = redact(section_text)
                items.append({
                    "id": item_id(source["id"], "note_section", line_start, line_end, text),
                    "sourceId": source["id"],
                    "kind": "note_section",
                    "text": text,
                    "capturedAt": captured_at,
                    "provenance": {
                        "path": rel,
                        "locatorType": "heading_section",
                        "lineStart": line_start,
                        "lineEnd": line_end,
                        "headingPath": heading_path_from_lines(lines, line_start),
                    },
                    "contentHash": f"sha256:{sha256_text(text)}",
                    "secretRedacted": redacted,
                    **({"observedAt": obs} if obs else {}),
                })
            current_heading = stripped
            section_lines = [(i, line)]
        elif current_heading:
            section_lines.append((i, line))

    # dedupe by id
    seen: set[str] = set()
    out: list[dict] = []
    for item in items:
        if item["id"] in seen:
            continue
        seen.add(item["id"])
        out.append(item)
    return out


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description="Ingest OpenClaw memory files into Mneme raw evidence JSONL.")
    ap.add_argument("--root", default=".", help="Workspace root")
    ap.add_argument("--out", default="raw", help="Output directory")
    args = ap.parse_args()

    root = Path(args.root).expanduser().resolve()
    out = Path(args.out).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)

    captured_at = iso_now()
    files = source_files(root)
    sources = [build_source(root, path, captured_at) for path in files]
    items: list[dict] = []
    for path, source in zip(files, sources):
        items.extend(build_items(root, path, source, captured_at))

    write_jsonl(out / "sources.jsonl", sources)
    write_jsonl(out / "items.jsonl", items)
    report = {
        "capturedAt": captured_at,
        "root": str(root),
        "sourceCount": len(sources),
        "itemCount": len(items),
        "sourceTypes": {k: sum(1 for s in sources if s["sourceType"] == k) for k in sorted({s["sourceType"] for s in sources})},
        "itemKinds": {k: sum(1 for it in items if it["kind"] == k) for k in sorted({it["kind"] for it in items})},
        "out": str(out),
    }
    (out / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
