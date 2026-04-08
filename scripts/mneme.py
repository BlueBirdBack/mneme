#!/usr/bin/env python3
"""Single operator CLI for Mneme.

This is a thin dispatch wrapper over the existing boring scripts so operators
have one obvious entrypoint.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COMMANDS = {
    "check": ROOT / "mneme_memory_check.py",
    "ingest": ROOT / "mneme_ingest_memory.py",
    "compile": ROOT / "mneme_compile_memory.py",
    "scrub": ROOT / "mneme_secret_scrub.py",
    "drift": ROOT / "mneme_memory_drift.py",
    "run": ROOT / "mneme_run.py",
    "retrieve": ROOT / "mneme_retrieve.py",
    "llm-roundtrip": ROOT / "mneme_llm_roundtrip.py",
    "runtime-task": ROOT / "mneme_runtime_orchestrate.py",
    "runtime-batch": ROOT / "mneme_runtime_batch.py",
}


def main() -> int:
    ap = argparse.ArgumentParser(description="Mneme operator CLI")
    ap.add_argument("command", choices=COMMANDS)
    ap.add_argument("args", nargs=argparse.REMAINDER)
    ns = ap.parse_args()

    cmd = [str(COMMANDS[ns.command]), *ns.args]
    cp = subprocess.run(cmd)
    return cp.returncode


if __name__ == "__main__":
    raise SystemExit(main())
