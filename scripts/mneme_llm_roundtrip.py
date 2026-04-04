#!/usr/bin/env python3
"""Run the Mneme LLM-assisted compile loop.

Flow:
1. ingest raw evidence
2. prepare LLM bundles
3. optionally validate + materialize one candidate file
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = {
    "ingest": ROOT / "mneme_ingest_memory.py",
    "prepare": ROOT / "mneme_llm_compile.py",
    "materialize": ROOT / "mneme_materialize_candidates.py",
}


def run_json(cmd: list[str], ok_codes: tuple[int, ...] = (0,)) -> dict:
    cp = subprocess.run(cmd, capture_output=True, text=True)
    if cp.returncode not in ok_codes:
        raise RuntimeError(f"Command failed ({cp.returncode}): {' '.join(cmd)}\n{cp.stderr or cp.stdout}")
    return json.loads(cp.stdout)


def main() -> int:
    ap = argparse.ArgumentParser(description="Run the Mneme LLM-assisted compile loop.")
    ap.add_argument("--root", default=".", help="Workspace root")
    ap.add_argument("--raw-out", default="/tmp/mneme-llm-raw", help="Raw evidence output dir")
    ap.add_argument("--bundles-out", default="/tmp/mneme-llm-bundles", help="Prepared bundle output dir")
    ap.add_argument("--category", required=True, choices=["projects", "systems", "decisions", "incidents", "people", "timeline"], help="Category to focus on")
    ap.add_argument("--max-items", type=int, default=60, help="Max evidence items per bundle")
    ap.add_argument("--candidate", help="Optional candidate JSON to validate/materialize")
    ap.add_argument("--materialize-out", default="/tmp/mneme-llm-materialized", help="Materialized output dir when --candidate is used")
    ap.add_argument("--json", action="store_true", help="Emit JSON summary")
    args = ap.parse_args()

    root = str(Path(args.root).expanduser().resolve())
    raw_out = str(Path(args.raw_out).expanduser().resolve())
    bundles_out = str(Path(args.bundles_out).expanduser().resolve())
    materialize_out = str(Path(args.materialize_out).expanduser().resolve())

    summary: dict[str, object] = {
        "root": root,
        "category": args.category,
        "steps": {},
    }

    summary["steps"]["ingest"] = run_json([
        str(TOOLS["ingest"]),
        "--root", root,
        "--out", raw_out,
    ])

    summary["steps"]["prepare"] = run_json([
        str(TOOLS["prepare"]),
        "prepare",
        "--raw", raw_out,
        "--out", bundles_out,
        "--max-items", str(args.max_items),
    ])

    category_bundles = [
        b for b in summary["steps"]["prepare"].get("bundles", [])
        if b.get("category") == args.category
    ]
    summary["steps"]["categoryBundles"] = category_bundles

    if args.candidate:
        candidate = str(Path(args.candidate).expanduser().resolve())
        summary["steps"]["validate"] = run_json([
            str(TOOLS["prepare"]),
            "validate",
            "--raw", raw_out,
            "--input", candidate,
        ], ok_codes=(0, 1))
        if not summary["steps"]["validate"].get("ok", False):
            if args.json:
                print(json.dumps(summary, indent=2))
            else:
                print(json.dumps(summary, indent=2))
            return 1
        summary["steps"]["materialize"] = run_json([
            str(TOOLS["materialize"]),
            "--category", args.category,
            "--input", candidate,
            "--out", materialize_out,
        ])

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print("Mneme LLM roundtrip")
        print("===================")
        print(f"root: {root}")
        print(f"category: {args.category}")
        ingest = summary["steps"]["ingest"]
        print(f"ingest: {ingest.get('sourceCount', 0)} sources, {ingest.get('itemCount', 0)} items")
        print(f"bundles for {args.category}: {len(category_bundles)}")
        if args.candidate:
            print(f"validate: {'ok' if summary['steps']['validate'].get('ok') else 'failed'}")
            if "materialize" in summary["steps"]:
                print(f"materialize: {summary['steps']['materialize'].get('entryCount', 0)} entries -> {summary['steps']['materialize'].get('out')} ")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        raise SystemExit(2)
