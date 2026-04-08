#!/usr/bin/env python3
"""Prepare/apply Mneme agent-connected compile runs.

This script is runtime-friendly:
- `prepare-task` builds raw evidence, bundles, and a ready-to-send agent prompt
- `apply-result` validates candidate JSON, materializes category output, and optionally merges reviewed packs

It does NOT directly spawn agents by itself. That remains the OpenClaw runtime/tool layer.
Preparing an agent task requires explicit export consent.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
TOOLS = {
    "roundtrip": ROOT / "mneme_llm_roundtrip.py",
    "validate": ROOT / "mneme_llm_compile.py",
    "materialize": ROOT / "mneme_materialize_candidates.py",
    "merge": ROOT / "mneme_merge_pack.py",
}

RULES = [
    "Output JSON only.",
    "Use only the evidence provided.",
    "Do not invent evidence refs.",
    "Prefer fewer stronger entries over many brittle entries.",
    "Group related evidence when it clearly belongs together.",
    "If evidence is historical, stale, or contradictory, reflect that in `state`.",
    "Every entry must have at least one evidence ref.",
]


def run_json(cmd: list[str], ok_codes: tuple[int, ...] = (0,)) -> dict[str, Any]:
    cp = subprocess.run(cmd, capture_output=True, text=True)
    if cp.returncode not in ok_codes:
        raise RuntimeError(f"Command failed ({cp.returncode}): {' '.join(cmd)}\n{cp.stderr or cp.stdout}")
    return json.loads(cp.stdout)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def build_task_prompt(category: str, bundle_payload: dict[str, Any]) -> str:
    lines = [
        "You are compiling Mneme candidate memory entries from raw evidence.",
        "",
        "Rules:",
        *[f"- {rule}" for rule in RULES],
        "",
        f"Category: {category}",
        "",
        "Return either a JSON array of entries or an object with an `entries` array. Nothing else.",
        "",
        "Bundle payload:",
        json.dumps(bundle_payload, ensure_ascii=False, indent=2),
    ]
    return "\n".join(lines)


def default_runtime_paths(root_path: Path) -> tuple[str, str, str]:
    base = root_path / ".mneme-runtime"
    return str(base / "raw"), str(base / "bundles"), str(base / "materialized")


def cmd_prepare_task(args: argparse.Namespace) -> int:
    if not args.allow_agent_export:
        raise RuntimeError(
            "Refusing to prepare an agent-export task without explicit consent. "
            "Re-run with --allow-agent-export."
        )

    root_path = Path(args.root).expanduser().resolve()
    default_raw_out, default_bundles_out, default_materialize_out = default_runtime_paths(root_path)

    root = str(root_path)
    raw_out = str(Path(args.raw_out).expanduser().resolve()) if args.raw_out else default_raw_out
    bundles_out = str(Path(args.bundles_out).expanduser().resolve()) if args.bundles_out else default_bundles_out
    materialize_out = str(Path(args.materialize_out).expanduser().resolve()) if args.materialize_out else default_materialize_out

    summary = run_json([
        str(TOOLS["roundtrip"]),
        "--root", root,
        "--category", args.category,
        "--raw-out", raw_out,
        "--bundles-out", bundles_out,
        "--max-items", str(args.max_items),
        "--json",
    ])
    category_bundles = summary["steps"]["categoryBundles"]
    if not category_bundles:
        raise RuntimeError(f"No bundles found for category {args.category}")
    bundle_meta = category_bundles[args.bundle_index]
    bundle_file = Path(bundles_out) / bundle_meta["file"]
    bundle_payload = load_json(bundle_file)
    task_prompt = build_task_prompt(args.category, bundle_payload)
    out = {
        "category": args.category,
        "bundleIndex": args.bundle_index,
        "bundleFile": str(bundle_file),
        "rawOut": raw_out,
        "bundlesOut": bundles_out,
        "materializeOut": materialize_out,
        "taskPrompt": task_prompt,
        "bundleMeta": bundle_meta,
        "summary": summary,
        "agentExportAllowed": True,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def cmd_apply_result(args: argparse.Namespace) -> int:
    raw_out = str(Path(args.raw_out).expanduser().resolve())
    candidate = str(Path(args.candidate).expanduser().resolve())
    materialize_out = str(Path(args.materialize_out).expanduser().resolve())

    validate = run_json([
        str(TOOLS["validate"]),
        "validate",
        "--raw", raw_out,
        "--input", candidate,
    ], ok_codes=(0, 1))

    out: dict[str, Any] = {"validate": validate}
    if not validate.get("ok", False):
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 1

    materialize = run_json([
        str(TOOLS["materialize"]),
        "--category", args.category,
        "--input", candidate,
        "--out", materialize_out,
    ])
    out["materialize"] = materialize

    if args.merge_out and args.merge_inputs:
        merge_out = str(Path(args.merge_out).expanduser().resolve())
        merge_cmd = [
            str(TOOLS["merge"]),
            "--inputs",
            *[str(Path(x).expanduser().resolve()) for x in args.merge_inputs],
            materialize_out,
            "--out", merge_out,
        ]
        out["merge"] = run_json(merge_cmd)

    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Prepare/apply Mneme runtime orchestration steps.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("prepare-task")
    p1.add_argument("--root", default=".")
    p1.add_argument("--category", required=True, choices=["projects", "systems", "decisions", "incidents", "people", "timeline"])
    p1.add_argument("--bundle-index", type=int, default=0)
    p1.add_argument("--max-items", type=int, default=60)
    p1.add_argument("--raw-out", default=None)
    p1.add_argument("--bundles-out", default=None)
    p1.add_argument("--materialize-out", default=None)
    p1.add_argument("--allow-agent-export", action="store_true", help="Explicitly allow preparing an off-box agent task payload")

    p2 = sub.add_parser("apply-result")
    p2.add_argument("--category", required=True, choices=["projects", "systems", "decisions", "incidents", "people", "timeline"])
    p2.add_argument("--raw-out", required=True)
    p2.add_argument("--candidate", required=True)
    p2.add_argument("--materialize-out", required=True)
    p2.add_argument("--merge-out")
    p2.add_argument("--merge-inputs", nargs="*")

    args = ap.parse_args()
    if args.cmd == "prepare-task":
        return cmd_prepare_task(args)
    return cmd_apply_result(args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        raise SystemExit(2)
