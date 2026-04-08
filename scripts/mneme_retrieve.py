#!/usr/bin/env python3
"""Retrieve Mneme evidence with inspectable citations.

This is a lexical-first recall helper that searches raw evidence and returns
ranked snippets with provenance. It is intentionally simple, local, and boring.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

STOPWORDS = {
    "the", "a", "an", "and", "or", "for", "to", "of", "in", "on", "with", "by",
    "is", "are", "was", "were", "be", "been", "it", "that", "this", "from", "as",
    "what", "which", "who", "when", "where", "how", "why", "about",
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(errors="replace").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"[A-Za-z0-9_./:-]+", text.lower()) if t not in STOPWORDS and len(t) >= 2]


def score_item(item: dict[str, Any], query_tokens: list[str], args: argparse.Namespace) -> int:
    prov = item.get("provenance") or {}
    heading_path = " > ".join(prov.get("headingPath") or [])
    haystacks = [
        (item.get("text") or ""),
        prov.get("path") or "",
        heading_path,
        item.get("kind") or "",
    ]
    text_blob = "\n".join(haystacks).lower()

    score = 0
    for token in query_tokens:
        if token in text_blob:
            score += 3
        if token in heading_path.lower():
            score += 2
        if token in (prov.get("path") or "").lower():
            score += 2

    if args.kind and item.get("kind") != args.kind:
        return 0
    if args.path and args.path.lower() not in (prov.get("path") or "").lower():
        return 0
    if args.heading and args.heading.lower() not in heading_path.lower():
        return 0
    observed_at = item.get("observedAt") or item.get("capturedAt") or ""
    if args.since and observed_at and observed_at < args.since:
        return 0
    if args.until and observed_at and observed_at > args.until:
        return 0
    return score


def citation(item: dict[str, Any]) -> dict[str, Any]:
    prov = item.get("provenance") or {}
    return {
        "evidenceItemId": item.get("id"),
        "path": prov.get("path"),
        "lineStart": prov.get("lineStart"),
        "lineEnd": prov.get("lineEnd"),
        "headingPath": prov.get("headingPath") or [],
        "observedAt": item.get("observedAt") or item.get("capturedAt"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Retrieve Mneme evidence with citations.")
    ap.add_argument("--root", default=".", help="Workspace root")
    ap.add_argument("--raw", default=None, help="Raw evidence directory (defaults to <root>/raw)")
    ap.add_argument("--query", required=True, help="Recall query")
    ap.add_argument("--kind", help="Optional evidence kind filter")
    ap.add_argument("--path", help="Optional path substring filter")
    ap.add_argument("--heading", help="Optional heading substring filter")
    ap.add_argument("--since", help="Optional ISO lower bound for observedAt/capturedAt")
    ap.add_argument("--until", help="Optional ISO upper bound for observedAt/capturedAt")
    ap.add_argument("--limit", type=int, default=8, help="Result limit")
    ap.add_argument("--json", action="store_true", help="Emit JSON")
    args = ap.parse_args()

    root = Path(args.root).expanduser().resolve()
    raw_dir = Path(args.raw).expanduser().resolve() if args.raw else (root / "raw")
    items = load_jsonl(raw_dir / "items.jsonl")
    query_tokens = tokenize(args.query)

    ranked: list[tuple[int, dict[str, Any]]] = []
    for item in items:
        score = score_item(item, query_tokens, args)
        if score > 0:
            ranked.append((score, item))
    ranked.sort(key=lambda x: (-x[0], x[1].get("observedAt") or x[1].get("capturedAt") or "", x[1].get("id") or ""))

    results = []
    for score, item in ranked[: args.limit]:
        results.append({
            "score": score,
            "kind": item.get("kind"),
            "text": item.get("text"),
            "citation": citation(item),
        })

    payload = {
        "query": args.query,
        "tokens": query_tokens,
        "raw": str(raw_dir),
        "count": len(results),
        "results": results,
    }

    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    print("Mneme Retrieval")
    print("===============")
    print(f"query: {args.query}")
    print(f"results: {len(results)}")
    print()
    for idx, result in enumerate(results, start=1):
        cite = result["citation"]
        heading = " > ".join(cite["headingPath"])
        line_range = f"{cite['lineStart']}-{cite['lineEnd']}" if cite.get("lineStart") else "?"
        print(f"{idx}. [{result['score']}] {result['text']}")
        print(f"   citation: {cite['path']}:{line_range}")
        if heading:
            print(f"   heading: {heading}")
        if cite.get("observedAt"):
            print(f"   observedAt: {cite['observedAt']}")
        print(f"   evidence: {cite['evidenceItemId']}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
