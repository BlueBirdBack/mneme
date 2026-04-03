#!/usr/bin/env python3
"""Merge materialized Mneme category outputs into one reviewed pack."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(errors="replace").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description="Merge materialized Mneme category outputs into one reviewed pack.")
    ap.add_argument("--inputs", nargs="+", required=True, help="Input category output directories")
    ap.add_argument("--out", required=True, help="Output reviewed pack directory")
    args = ap.parse_args()

    out_dir = Path(args.out).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    documents: list[dict[str, Any]] = []
    entries: list[dict[str, Any]] = []
    categories: list[str] = []

    for raw_in in args.inputs:
        in_dir = Path(raw_in).expanduser().resolve()
        docs = load_jsonl(in_dir / "documents.jsonl")
        ents = load_jsonl(in_dir / "entries.jsonl")
        documents.extend(docs)
        entries.extend(ents)
        for doc in docs:
            categories.append(doc.get("kind", "unknown"))
        for md in in_dir.glob("*.md"):
            if md.name in {"projects.md", "systems.md", "decisions.md", "incidents.md", "people.md", "timeline.md"}:
                (out_dir / md.name).write_text(md.read_text(errors="replace"))

    write_jsonl(out_dir / "documents.jsonl", documents)
    write_jsonl(out_dir / "entries.jsonl", entries)

    report = {
        "categoryCount": len(categories),
        "categories": categories,
        "documentCount": len(documents),
        "entryCount": len(entries),
        "inputs": [str(Path(x).expanduser().resolve()) for x in args.inputs],
        "out": str(out_dir),
    }
    (out_dir / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))

    lines = [
        "# Mneme Reviewed Pack",
        "",
        "> Merged reviewed category outputs.",
        "",
        f"- Categories: {', '.join(categories)}",
        f"- Documents: {len(documents)}",
        f"- Entries: {len(entries)}",
        "",
        "## Included views",
    ]
    for name in ["projects.md", "systems.md", "decisions.md", "incidents.md", "people.md", "timeline.md"]:
        if (out_dir / name).exists():
            lines.append(f"- `{name}`")
    lines.extend(["", "## Inputs", *[f"- `{Path(x).expanduser().resolve()}`" for x in args.inputs], ""])
    (out_dir / "README.md").write_text("\n".join(lines))

    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
