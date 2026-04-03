#!/usr/bin/env python3
"""Prepare and validate LLM-assisted Mneme compile passes.

This script does NOT replace the deterministic pipeline.
It wraps an LLM judgment step with stable input bundles and output validation.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

CATEGORY_CONFIG = {
    "projects": {
        "include": [
            r"\bproject\b", r"\brepo\b", r"\bbranch\b", r"\bdeploy\b", r"\bworktree\b",
            r"\bcheckout\b", r"\bdemo\b", r"\bfrontend\b", r"\bbaseurl\b", r"\b/map\b",
            r"\bgeo\b", r"\btruth layer\b",
        ],
        "exclude": [
            r"\bnats\b", r"\bmysql\b", r"\bmqtt\b", r"\bssh\b", r"\bgateway\b",
            r"\btoken\b", r"\bcert\b", r"\bservice(s)?\b", r"\bapi key\b", r"\bport\b",
        ],
        "headingHints": [r"active projects", r"durable project facts", r"bdeep", r"yibin", r"aqua", r"mneme"],
    },
    "systems": {
        "include": [
            r"\bhost\b", r"\bserver\b", r"\bssh\b", r"\bgateway\b", r"\bnats\b",
            r"\bmemory\b", r"\bmysql\b", r"\bmqtt\b", r"\bforgejo\b", r"\bapi\b",
            r"\bservice(s)?\b", r"\bwebsocket\b", r"\btunnel\b", r"\bcert\b", r"\bport\b",
        ],
        "exclude": [r"\bbounty\b", r"\bissue\b", r"\bdecision\b"],
        "headingHints": [r"systems", r"infrastructure", r"key infrastructure", r"access", r"memory stack"],
    },
    "decisions": {
        "include": [
            r"\bdecision\b", r"\bhard rule\b", r"\bdo not\b", r"\bmust\b", r"\bshould\b",
            r"\bprefer\b", r"\brule\b", r"\bchosen\b", r"\blocked\b", r"\bkeep\b",
            r"\bprimary target\b", r"\bintentional\b", r"\barchitecture decision\b",
        ],
        "exclude": [r"\bissue\b", r"\boutage\b", r"\bfailed\b"],
        "headingHints": [r"decisions", r"durable decisions", r"preferences", r"methods"],
    },
    "incidents": {
        "include": [
            r"\bincident\b", r"\broot cause\b", r"\boutage\b", r"\bfailed\b", r"\bbroken\b",
            r"\bcompromise\b", r"\bspike\b", r"\bcpu\b", r"\bram\b", r"\bfix\b",
            r"\balert\b", r"\battack\b", r"\bproblem\b",
        ],
        "exclude": [],
        "headingHints": [r"incidents", r"warnings", r"supply chain"],
    },
}

CATEGORY_PRIORITY = {"incidents": 4, "decisions": 3, "systems": 2, "projects": 1}
VALID_STATES = {"observed", "inferred", "stale", "contradicted", "historical"}

SYSTEM_PROMPT = """You are compiling Mneme candidate memory entries from raw evidence.

Rules:
- Output JSON only.
- Use only the evidence provided.
- Do not invent evidence refs.
- Prefer fewer stronger entries over many brittle entries.
- Group related evidence when it clearly belongs together.
- If evidence is historical, stale, or contradictory, reflect that in `state`.
- Every entry must have at least one evidence ref.
"""


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(errors="replace").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def score_category(text: str, heading_path: list[str], category: str) -> int:
    cfg = CATEGORY_CONFIG[category]
    tl = text.lower()
    hl = " > ".join(heading_path).lower()
    score = 0
    for pat in cfg["include"]:
        if re.search(pat, tl):
            score += 2
    for pat in cfg.get("headingHints", []):
        if re.search(pat, hl):
            score += 1
    for pat in cfg.get("exclude", []):
        if re.search(pat, tl):
            score -= 2
    return score


def classify_item(item: dict[str, Any]) -> str | None:
    text = (item.get("text") or "").strip()
    if not text:
        return None
    heading_path = list((item.get("provenance") or {}).get("headingPath") or [])
    best_category = None
    best_score = 0
    for category in CATEGORY_CONFIG:
        score = score_category(text, heading_path, category)
        if score > best_score or (score == best_score and score > 0 and best_category and CATEGORY_PRIORITY[category] > CATEGORY_PRIORITY[best_category]):
            best_category = category
            best_score = score
    return best_category if best_score > 0 else None


def chunked(seq: list[Any], size: int) -> list[list[Any]]:
    return [seq[i:i + size] for i in range(0, len(seq), size)]


def prepare(raw_dir: Path, out_dir: Path, max_items: int) -> dict[str, Any]:
    items = load_jsonl(raw_dir / "items.jsonl")
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        category = classify_item(item)
        if category:
            grouped[category].append(item)

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "SYSTEM_PROMPT.md").write_text(SYSTEM_PROMPT)

    manifest = {
        "rawDir": str(raw_dir),
        "bundleCount": 0,
        "bundles": [],
    }

    for category in sorted(grouped):
        category_items = sorted(
            grouped[category],
            key=lambda x: (
                x.get("observedAt") or "",
                (x.get("provenance") or {}).get("path") or "",
                (x.get("provenance") or {}).get("lineStart") or 0,
            ),
        )
        for idx, bundle_items in enumerate(chunked(category_items, max_items), start=1):
            name = f"bundle-{category}-{idx:02d}.json"
            payload = {
                "category": category,
                "instructions": {
                    "outputShape": {
                        "entries": [
                            {
                                "title": "string",
                                "summary": "string",
                                "state": "observed|inferred|stale|contradicted|historical",
                                "tags": ["string"],
                                "facts": [
                                    {
                                        "key": "string",
                                        "value": "string|number|boolean|object",
                                        "state": "observed|inferred|stale|contradicted|historical",
                                        "evidenceRefs": [{"evidenceItemId": "string"}],
                                    }
                                ],
                                "relations": [
                                    {
                                        "type": "depends_on|related_to|supersedes|derived_from|owned_by|affects",
                                        "targetTitle": "string",
                                        "state": "observed|inferred|stale|contradicted|historical",
                                    }
                                ],
                                "evidenceRefs": [{"evidenceItemId": "string"}],
                            }
                        ]
                    },
                    "rules": [
                        "Use only supplied evidence.",
                        "Do not invent evidence ids.",
                        "Prefer fewer stronger entries.",
                        "Group related evidence when justified.",
                    ],
                },
                "evidenceItems": [
                    {
                        "id": item["id"],
                        "text": item.get("text"),
                        "observedAt": item.get("observedAt"),
                        "kind": item.get("kind"),
                        "provenance": item.get("provenance"),
                    }
                    for item in bundle_items
                ],
            }
            (out_dir / name).write_text(json.dumps(payload, indent=2, ensure_ascii=False))
            manifest["bundles"].append({
                "file": name,
                "category": category,
                "itemCount": len(bundle_items),
            })

    manifest["bundleCount"] = len(manifest["bundles"])
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    return manifest


def validate(raw_dir: Path, candidate_file: Path) -> dict[str, Any]:
    raw_items = {row["id"] for row in load_jsonl(raw_dir / "items.jsonl")}
    payload = json.loads(candidate_file.read_text())
    entries = payload["entries"] if isinstance(payload, dict) else payload
    errors: list[str] = []

    if not isinstance(entries, list):
        raise ValueError("Candidate output must be a list or an object with `entries`.")

    for idx, entry in enumerate(entries, start=1):
        prefix = f"entry[{idx}]"
        for field in ("title", "summary", "state", "evidenceRefs"):
            if field not in entry:
                errors.append(f"{prefix}: missing `{field}`")
        if "state" in entry and entry["state"] not in VALID_STATES:
            errors.append(f"{prefix}: invalid state `{entry['state']}`")
        refs = entry.get("evidenceRefs", [])
        if not isinstance(refs, list) or not refs:
            errors.append(f"{prefix}: `evidenceRefs` must be a non-empty list")
        else:
            for ridx, ref in enumerate(refs, start=1):
                evid = ref.get("evidenceItemId")
                if not evid:
                    errors.append(f"{prefix}: evidenceRefs[{ridx}] missing `evidenceItemId`")
                elif evid not in raw_items:
                    errors.append(f"{prefix}: unknown evidence ref `{evid}`")
        facts = entry.get("facts", [])
        if facts is not None:
            if not isinstance(facts, list):
                errors.append(f"{prefix}: `facts` must be a list")
            else:
                for fidx, fact in enumerate(facts, start=1):
                    if "key" not in fact or "value" not in fact or "evidenceRefs" not in fact:
                        errors.append(f"{prefix}: facts[{fidx}] missing required fields")
        relations = entry.get("relations", [])
        if relations is not None and not isinstance(relations, list):
            errors.append(f"{prefix}: `relations` must be a list")

    return {
        "ok": not errors,
        "entryCount": len(entries),
        "errors": errors,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Prepare and validate LLM-assisted Mneme compile passes.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("prepare")
    p1.add_argument("--raw", required=True, help="Directory containing raw/items.jsonl")
    p1.add_argument("--out", required=True, help="Output directory for LLM bundles")
    p1.add_argument("--max-items", type=int, default=60, help="Max evidence items per bundle")

    p2 = sub.add_parser("validate")
    p2.add_argument("--raw", required=True, help="Directory containing raw/items.jsonl")
    p2.add_argument("--input", required=True, help="Candidate JSON file from LLM")

    args = ap.parse_args()
    if args.cmd == "prepare":
        result = prepare(Path(args.raw).expanduser().resolve(), Path(args.out).expanduser().resolve(), args.max_items)
    else:
        result = validate(Path(args.raw).expanduser().resolve(), Path(args.input).expanduser().resolve())
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
