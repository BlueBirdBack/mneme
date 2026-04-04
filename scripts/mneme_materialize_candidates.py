#!/usr/bin/env python3
"""Materialize validated LLM candidate entries into compiled Mneme outputs."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DOCUMENT_TITLES = {
    "projects": "Compiled Projects",
    "systems": "Compiled Systems",
    "decisions": "Compiled Decisions",
    "incidents": "Compiled Incidents",
    "people": "Compiled People",
    "timeline": "Compiled Timeline",
}

ENTRY_TYPES = {
    "projects": "project",
    "systems": "system",
    "decisions": "decision",
    "incidents": "incident",
    "people": "person",
    "timeline": "timeline_event",
}


def slugify(text: str, limit: int = 48) -> str:
    s = text.lower()
    s = re.sub(r"[`*_#\[\](){}:;,.!?]+", " ", s)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:limit] or "entry"


def load_candidate(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text())
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("entries"), list):
        return payload["entries"]
    raise ValueError("Candidate file must be a list or an object with `entries`.")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def build_markdown(category: str, entries: list[dict[str, Any]]) -> str:
    lines = [
        f"# {DOCUMENT_TITLES[category]}",
        "",
        "> Materialized from validated LLM candidate entries.",
        "",
    ]
    for entry in entries:
        lines.append(f"## {entry['title']}")
        lines.append("")
        lines.append(entry["summary"])
        lines.append("")
        lines.append(f"- Entry: `{entry['id']}`")
        lines.append(f"- State: `{entry['state']}`")
        if entry.get("tags"):
            lines.append(f"- Tags: {', '.join(entry['tags'])}")
        refs = [r["evidenceItemId"] for r in entry.get("evidenceRefs", [])]
        if refs:
            lines.append(f"- Evidence refs: {', '.join(f'`{r}`' for r in refs[:6])}")
            if len(refs) > 6:
                lines.append(f"- … {len(refs)-6} more evidence refs")
        facts = entry.get("facts", [])
        if facts:
            lines.append("")
            lines.append("### Facts")
            for fact in facts[:12]:
                lines.append(f"- **{fact['key']}**: {fact['value']}")
            if len(facts) > 12:
                lines.append(f"- … {len(facts)-12} more")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Materialize validated LLM candidate entries into compiled outputs.")
    ap.add_argument("--category", required=True, choices=sorted(DOCUMENT_TITLES))
    ap.add_argument("--input", required=True, help="Validated candidate JSON")
    ap.add_argument("--out", required=True, help="Output directory")
    args = ap.parse_args()

    category = args.category
    raw_entries = load_candidate(Path(args.input).expanduser().resolve())
    out_dir = Path(args.out).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    document_id = f"doc:compiled:{category}"
    entries: list[dict[str, Any]] = []
    for idx, raw in enumerate(raw_entries, start=1):
        entry = dict(raw)
        entry["id"] = f"cmp:{ENTRY_TYPES[category]}:{slugify(entry['title'])}-{idx:03d}"
        entry["documentId"] = document_id
        entry.setdefault("entryType", ENTRY_TYPES[category])
        entry.setdefault("updatedAt", generated_at)
        entries.append(entry)

    document = {
        "id": document_id,
        "kind": category,
        "title": DOCUMENT_TITLES[category],
        "generatedAt": generated_at,
        "entryIds": [e["id"] for e in entries],
        "sourceIds": [],
        "meta": {
            "materializedFrom": str(Path(args.input).expanduser().resolve()),
        },
    }

    write_jsonl(out_dir / "documents.jsonl", [document])
    write_jsonl(out_dir / "entries.jsonl", entries)
    (out_dir / f"{category}.md").write_text(build_markdown(category, entries))
    print(json.dumps({
        "ok": True,
        "category": category,
        "documentId": document_id,
        "entryCount": len(entries),
        "out": str(out_dir),
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
