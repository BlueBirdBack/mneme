#!/usr/bin/env python3
"""Prepare/apply multi-category Mneme runtime runs.

This sits one level above `mneme_runtime_orchestrate.py`.
It does not directly dispatch agents; it prepares per-category tasks and can
apply multiple returned candidate files plus merge the reviewed pack.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
ORCH = ROOT / "mneme_runtime_orchestrate.py"

DEFAULT_CATEGORIES = ["projects", "systems", "decisions", "incidents", "people", "timeline"]


def run_json(cmd: list[str], ok_codes: tuple[int, ...] = (0,)) -> dict[str, Any]:
    cp = subprocess.run(cmd, capture_output=True, text=True)
    if cp.returncode not in ok_codes:
        raise RuntimeError(f"Command failed ({cp.returncode}): {' '.join(cmd)}\n{cp.stderr or cp.stdout}")
    return json.loads(cp.stdout)


def prepare_batch(args: argparse.Namespace) -> dict[str, Any]:
    root = str(Path(args.root).expanduser().resolve())
    base_out = Path(args.out).expanduser().resolve()
    base_out.mkdir(parents=True, exist_ok=True)
    raw_out = base_out / "raw"
    bundles_out = base_out / "bundles"
    materialized_base = base_out / "materialized"

    categories = args.categories or DEFAULT_CATEGORIES
    tasks: list[dict[str, Any]] = []
    for category in categories:
        materialize_out = materialized_base / category
        result = run_json([
            str(ORCH), "prepare-task",
            "--root", root,
            "--category", category,
            "--bundle-index", str(args.bundle_index),
            "--max-items", str(args.max_items),
            "--raw-out", str(raw_out),
            "--bundles-out", str(bundles_out),
            "--materialize-out", str(materialize_out),
        ])
        task_file = base_out / f"task-{category}.json"
        task_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
        tasks.append({
            "category": category,
            "taskFile": str(task_file),
            "bundleFile": result["bundleFile"],
            "materializeOut": result["materializeOut"],
            "bundleMeta": result["bundleMeta"],
        })

    manifest = {
        "root": root,
        "out": str(base_out),
        "rawOut": str(raw_out),
        "bundlesOut": str(bundles_out),
        "categories": categories,
        "tasks": tasks,
    }
    (base_out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    return manifest


def apply_batch(args: argparse.Namespace) -> dict[str, Any]:
    manifest = json.loads(Path(args.manifest).expanduser().resolve().read_text())
    raw_out = manifest["rawOut"]
    reviewed_out = str(Path(args.reviewed_out).expanduser().resolve())

    applied: list[dict[str, Any]] = []
    materialized_dirs: list[str] = []

    for mapping in args.candidate_map:
        if "=" not in mapping:
            raise RuntimeError(f"Invalid candidate mapping: {mapping} (expected category=/path/file.json)")
        category, candidate = mapping.split("=", 1)
        task = next((t for t in manifest["tasks"] if t["category"] == category), None)
        if not task:
            raise RuntimeError(f"Category {category} not found in manifest")
        result = run_json([
            str(ORCH), "apply-result",
            "--category", category,
            "--raw-out", raw_out,
            "--candidate", str(Path(candidate).expanduser().resolve()),
            "--materialize-out", task["materializeOut"],
        ], ok_codes=(0, 1))
        applied.append({"category": category, **result})
        if result.get("validate", {}).get("ok") and "materialize" in result:
            materialized_dirs.append(task["materializeOut"])

    merge = None
    if materialized_dirs:
        merge = run_json([
            str(ROOT / "mneme_merge_pack.py"),
            "--inputs", *materialized_dirs,
            "--out", reviewed_out,
        ])

    return {
        "manifest": manifest,
        "applied": applied,
        "merge": merge,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Prepare/apply multi-category Mneme runtime runs.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("prepare-batch")
    p1.add_argument("--root", default=".")
    p1.add_argument("--out", required=True)
    p1.add_argument("--categories", nargs="*", choices=DEFAULT_CATEGORIES)
    p1.add_argument("--bundle-index", type=int, default=0)
    p1.add_argument("--max-items", type=int, default=25)

    p2 = sub.add_parser("apply-batch")
    p2.add_argument("--manifest", required=True)
    p2.add_argument("--candidate-map", nargs="+", required=True, help="category=/path/to/candidate.json")
    p2.add_argument("--reviewed-out", required=True)

    args = ap.parse_args()
    if args.cmd == "prepare-batch":
        out = prepare_batch(args)
    else:
        out = apply_batch(args)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        raise SystemExit(2)
