#!/usr/bin/env python3
"""Mneme memory health check for OpenClaw.

Purpose:
- detect broken memory provider configuration
- detect missing local embedding dependencies
- detect stale or missing memory indexes
- surface clear failure reasons and suggested fixes

This is intentionally small and dependency-free.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CONFIG_PATH = Path.home() / ".openclaw" / "openclaw.json"
OPENCLAW_BIN = shutil.which("openclaw") or "openclaw"


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str
    fix: str | None = None


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True)


def load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    return json.loads(path.read_text())


def deep_get(obj: dict[str, Any], *keys: str) -> Any:
    cur: Any = obj
    for key in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def detect_local_embedding_dependency() -> tuple[bool, str]:
    """Return whether local embeddings appear available.

    This is heuristic on purpose. Mneme cares about practical breakage more than
    perfect package introspection.
    """
    base = Path.home() / ".openclaw" / "tools"
    if not base.exists():
        return False, f"OpenClaw tools directory not found at {base}"

    candidates = list(base.glob("node-*/lib/node_modules/openclaw/node_modules/node-llama-cpp"))
    if candidates:
        return True, f"Found node-llama-cpp at {candidates[0]}"
    return False, "node-llama-cpp not found under ~/.openclaw/tools"


def parse_memory_status(text: str) -> dict[str, Any]:
    parsed: dict[str, Any] = {"raw": text}
    patterns = {
        "provider": r"^Provider:\s+(.+)$",
        "model": r"^Model:\s+(.+)$",
        "indexed": r"^Indexed:\s+(.+)$",
        "dirty": r"^Dirty:\s+(.+)$",
        "store": r"^Store:\s+(.+)$",
        "embeddings": r"^Embeddings:\s+(.+)$",
        "vector": r"^Vector:\s+(.+)$",
        "fts": r"^FTS:\s+(.+)$",
    }
    for key, pattern in patterns.items():
        m = re.search(pattern, text, re.MULTILINE)
        if m:
            parsed[key] = m.group(1).strip()

    m = re.search(r"^Indexed:\s+(\d+)/(\d+) files\s+·\s+(\d+) chunks$", text, re.MULTILINE)
    if m:
        parsed["indexed_files"] = int(m.group(1))
        parsed["total_files"] = int(m.group(2))
        parsed["chunks"] = int(m.group(3))

    return parsed


def check_config(config: dict[str, Any]) -> list[CheckResult]:
    provider = deep_get(config, "agents", "defaults", "memorySearch", "provider")
    enabled = deep_get(config, "agents", "defaults", "memorySearch", "enabled")
    results: list[CheckResult] = []

    if enabled is False:
        results.append(
            CheckResult(
                "memory_search_enabled",
                False,
                "Memory search is explicitly disabled.",
                "Set agents.defaults.memorySearch.enabled=true.",
            )
        )
    else:
        results.append(CheckResult("memory_search_enabled", True, "Memory search is enabled or implicitly on."))

    if not provider:
        results.append(
            CheckResult(
                "provider_configured",
                False,
                "No memory search provider is configured.",
                "Set agents.defaults.memorySearch.provider to gemini, openai, voyage, mistral, ollama, or local.",
            )
        )
        return results

    results.append(CheckResult("provider_configured", True, f"Provider configured: {provider}"))

    if provider == "local":
        ok, detail = detect_local_embedding_dependency()
        results.append(
            CheckResult(
                "local_embedding_dependency",
                ok,
                detail,
                None if ok else "Install/rebuild node-llama-cpp or switch to a working remote provider such as gemini.",
            )
        )

    return results


def check_memory_status() -> tuple[list[CheckResult], dict[str, Any], subprocess.CompletedProcess[str] | None]:
    cp = run([OPENCLAW_BIN, "memory", "status", "--deep"])
    if cp.returncode != 0:
        text = (cp.stderr or "") + "\n" + (cp.stdout or "")
        text = text.strip()
        fix = "Inspect `openclaw memory status --deep` output."
        if "node-llama-cpp" in text:
            fix = "Local embeddings are unavailable. Install/rebuild node-llama-cpp or switch to a working remote provider."
        elif "provider" in text.lower() and "memory" in text.lower():
            fix = "Check agents.defaults.memorySearch.provider and API keys."
        return (
            [CheckResult("memory_status", False, text or "`openclaw memory status --deep` failed.", fix)],
            {},
            cp,
        )

    parsed = parse_memory_status(cp.stdout)
    results: list[CheckResult] = [CheckResult("memory_status", True, "`openclaw memory status --deep` succeeded.")]

    dirty = parsed.get("dirty")
    if dirty and dirty.lower() != "no":
        results.append(
            CheckResult(
                "index_freshness",
                False,
                f"Index reports Dirty={dirty}.",
                "Run `openclaw memory index --force` and re-check.",
            )
        )
    else:
        results.append(CheckResult("index_freshness", True, f"Index dirty state: {dirty or 'unknown'}"))

    indexed_files = parsed.get("indexed_files", 0)
    chunks = parsed.get("chunks", 0)
    if indexed_files <= 0 or chunks <= 0:
        results.append(
            CheckResult(
                "index_populated",
                False,
                f"Index appears empty (files={indexed_files}, chunks={chunks}).",
                "Write memory files and run `openclaw memory index --force`.",
            )
        )
    else:
        results.append(CheckResult("index_populated", True, f"Indexed files={indexed_files}, chunks={chunks}"))

    embeddings = (parsed.get("embeddings") or "").lower()
    if embeddings and embeddings != "ready":
        results.append(
            CheckResult(
                "embeddings_ready",
                False,
                f"Embeddings state is `{parsed.get('embeddings')}`.",
                "Check provider health, API keys, and memory provider configuration.",
            )
        )
    else:
        results.append(CheckResult("embeddings_ready", True, f"Embeddings state: {parsed.get('embeddings', 'unknown')}"))

    return results, parsed, cp


DEFAULT_QUERIES = [
    "Ash SSH port",
    "BDeep v2 deploy",
]


def run_query_check(queries: list[str]) -> list[CheckResult]:
    results: list[CheckResult] = []
    for query in queries:
        cp = run([OPENCLAW_BIN, "memory", "search", query])
        if cp.returncode != 0:
            results.append(
                CheckResult(
                    f"query:{query}",
                    False,
                    f"Query failed: {query}\n{(cp.stderr or cp.stdout).strip()}",
                    "Inspect the memory search backend and provider configuration.",
                )
            )
            continue

        output = cp.stdout.strip()
        if not output:
            results.append(
                CheckResult(
                    f"query:{query}",
                    False,
                    f"Query returned no output: {query}",
                    "Check whether the index contains relevant memory and whether search ranking is working.",
                )
            )
            continue

        source_like = bool(re.search(r"(^|\n)\d*\.?\d+\s+\S+\.md:\d+-\d+", output))
        results.append(
            CheckResult(
                f"query:{query}",
                True,
                f"Query returned results for: {query}",
                None if source_like else "Results were returned but source formatting was unexpected; inspect citation formatting.",
            )
        )
    return results


def render(results: list[CheckResult], status: dict[str, Any], json_mode: bool) -> int:
    failed = [r for r in results if not r.ok]
    if json_mode:
        payload = {
            "ok": not failed,
            "summary": {
                "checks": len(results),
                "failed": len(failed),
            },
            "status": status,
            "results": [r.__dict__ for r in results],
        }
        print(json.dumps(payload, indent=2))
        return 1 if failed else 0

    print("Mneme Memory Check")
    print("==================")
    if status:
        provider = status.get("provider", "unknown")
        indexed = status.get("indexed", "unknown")
        print(f"Provider: {provider}")
        print(f"Indexed:  {indexed}")
        print()

    for r in results:
        badge = "PASS" if r.ok else "FAIL"
        print(f"[{badge}] {r.name}: {r.detail}")
        if r.fix:
            print(f"       fix: {r.fix}")

    print()
    if failed:
        print(f"Result: FAIL ({len(failed)}/{len(results)} checks failed)")
        return 1

    print(f"Result: PASS ({len(results)} checks)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Mneme memory health checks against OpenClaw.")
    parser.add_argument("--config", default=str(CONFIG_PATH), help="Path to openclaw.json")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text")
    parser.add_argument(
        "--skip-query-checks",
        action="store_true",
        help="Skip live memory search queries and only run config/status checks.",
    )
    parser.add_argument(
        "--query",
        action="append",
        default=[],
        help="Add a memory search query to verify live recall. Can be passed multiple times.",
    )
    args = parser.parse_args()

    config = load_config(Path(args.config).expanduser())
    results = check_config(config)
    status_results, status, _cp = check_memory_status()
    results.extend(status_results)

    if not args.skip_query_checks:
        queries = args.query or DEFAULT_QUERIES
        results.extend(run_query_check(queries))

    return render(results, status, args.json)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except FileNotFoundError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        raise SystemExit(2)
