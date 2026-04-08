#!/usr/bin/env python3
"""Retrieve Mneme evidence with inspectable citations.

This started as a lexical-first recall helper over raw evidence.
It now also has an activity-oriented retrieval mode for recent-work questions,
so operators can combine durable evidence with recent session and git signals.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

STOPWORDS = {
    "the", "a", "an", "and", "or", "for", "to", "of", "in", "on", "with", "by",
    "is", "are", "was", "were", "be", "been", "it", "that", "this", "from", "as",
    "what", "which", "who", "when", "where", "how", "why", "about", "did", "do",
    "does", "have", "has", "had", "you", "your", "latest", "last", "recent", "today",
    "yesterday", "hours", "hour", "days", "day", "past", "done", "changed", "change",
    "working", "worked",
}
ACTIVITY_QUERY_PATTERNS = [
    re.compile(r"\bwhat (?:did|have) you (?:do|done)\b", re.I),
    re.compile(r"\bwhat changed\b", re.I),
    re.compile(r"\brecent work\b", re.I),
    re.compile(r"\brecent activity\b", re.I),
    re.compile(r"\bworking on\b", re.I),
    re.compile(r"\b(?:last|latest)\s+\d+\s+(?:hour|hours|day|days)\b", re.I),
    re.compile(r"\btoday\b", re.I),
    re.compile(r"\byesterday\b", re.I),
]
IGNORED_REPO_DIRS = {
    ".git", ".venv", "venv", "node_modules", "raw", "compiled", ".pytest_cache", "__pycache__",
}
LOW_SIGNAL_SESSION_PATTERNS = [
    re.compile(r"^\[cron:", re.I),
    re.compile(r"^HEARTBEAT_OK$", re.I),
]


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


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def format_z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def within_range(value: str | None, since: str | None, until: str | None) -> bool:
    dt = parse_dt(value)
    if dt is None:
        return True
    since_dt = parse_dt(since)
    until_dt = parse_dt(until)
    if since_dt and dt < since_dt:
        return False
    if until_dt and dt > until_dt:
        return False
    return True


def is_activity_query(query: str) -> bool:
    return any(p.search(query) for p in ACTIVITY_QUERY_PATTERNS)


def infer_time_bounds(query: str, since: str | None, until: str | None) -> tuple[str | None, str | None, bool]:
    if since or until:
        return since, until, False

    now = datetime.now(timezone.utc)
    q = query.lower()

    m = re.search(r"\b(?:last|latest)\s+(\d+)\s+hours?\b", q)
    if m:
        return format_z(now - timedelta(hours=int(m.group(1)))), None, True

    m = re.search(r"\b(?:last|latest)\s+(\d+)\s+days?\b", q)
    if m:
        return format_z(now - timedelta(days=int(m.group(1)))), None, True

    if "yesterday" in q:
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday = today - timedelta(days=1)
        return format_z(yesterday), format_z(today), True

    if "today" in q:
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return format_z(today), None, True

    if is_activity_query(query):
        return format_z(now - timedelta(days=7)), None, True

    return None, None, False


def discover_git_repos(root: Path, max_depth: int = 3) -> list[Path]:
    repos: list[Path] = []
    for current, dirnames, _filenames in os.walk(root):
        current_path = Path(current)
        try:
            rel = current_path.relative_to(root)
            depth = len(rel.parts)
        except ValueError:
            depth = 0
        if ".git" in dirnames:
            repos.append(current_path)
            dirnames.remove(".git")
        dirnames[:] = [d for d in dirnames if d not in IGNORED_REPO_DIRS]
        if depth >= max_depth:
            dirnames[:] = []
    unique: list[Path] = []
    seen: set[str] = set()
    for repo in repos:
        key = str(repo.resolve())
        if key not in seen:
            seen.add(key)
            unique.append(repo)
    return unique


def run_capture(cmd: list[str]) -> str:
    cp = subprocess.run(cmd, capture_output=True, text=True)
    if cp.returncode != 0:
        return ""
    return cp.stdout


def load_git_activity(root: Path, since: str | None, until: str | None, limit_per_repo: int = 25, max_depth: int = 3) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for repo in discover_git_repos(root, max_depth=max_depth):
        cmd = [
            "git", "-C", str(repo), "log", "--no-merges",
            f"--max-count={limit_per_repo}",
            "--pretty=format:%H%x1f%aI%x1f%s%x1f%D",
        ]
        if since:
            cmd.append(f"--since={since}")
        if until:
            cmd.append(f"--until={until}")
        output = run_capture(cmd)
        if not output.strip():
            continue
        for line in output.splitlines():
            parts = line.split("\x1f")
            if len(parts) < 4:
                continue
            sha, observed_at, subject, refs = parts[:4]
            rel_repo = repo.relative_to(root) if repo != root else Path(".")
            items.append({
                "id": f"git:{rel_repo}:{sha[:12]}",
                "kind": "git_commit",
                "text": f"[{rel_repo}] {subject}",
                "observedAt": observed_at,
                "provenance": {
                    "path": f"{rel_repo}/.git",
                    "headingPath": ["git", str(rel_repo)],
                    "repo": str(rel_repo),
                    "commit": sha,
                    "refs": refs,
                },
            })
    return items


def extract_message_text(message: dict[str, Any]) -> str:
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    if not isinstance(content, list):
        return ""
    texts: list[str] = []
    for part in content:
        if not isinstance(part, dict):
            continue
        if part.get("type") == "text" and part.get("text"):
            texts.append(str(part.get("text")).strip())
    return " ".join(t for t in texts if t).strip()


def normalize_session_prompt_text(text: str) -> str:
    if not text:
        return ""
    for pat in LOW_SIGNAL_SESSION_PATTERNS:
        if pat.search(text.strip()):
            return ""

    if "Conversation info (untrusted metadata):" in text or "Sender (untrusted metadata):" in text:
        text = re.sub(r"```.*?```", "", text, flags=re.S)
        filtered: list[str] = []
        for line in text.splitlines():
            s = line.strip()
            if not s:
                continue
            if "untrusted metadata" in s.lower():
                continue
            if s.lower().startswith("sender ("):
                continue
            if s.lower().startswith("replied message ("):
                continue
            filtered.append(s)
        text = " ".join(filtered).strip()

    return text[:4000].strip()


def load_session_activity(session_root: Path, since: str | None, until: str | None, limit_files: int = 200) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if not session_root.exists():
        return items

    session_files = sorted(session_root.rglob("*.jsonl"))[:limit_files]
    for path in session_files:
        rel = path.relative_to(session_root)
        try:
            with path.open("r", encoding="utf-8", errors="replace") as fh:
                for raw_line in fh:
                    line = raw_line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    if path.name.endswith(".acp-stream.jsonl"):
                        observed_at = obj.get("ts") or obj.get("timestamp")
                        if not within_range(observed_at, since, until):
                            continue
                        text = (obj.get("text") or "").strip()
                        kind = obj.get("kind") or "session_event"
                        if not text or kind == "assistant_delta":
                            continue
                        items.append({
                            "id": f"session:{rel}:{obj.get('epochMs') or observed_at}:{kind}",
                            "kind": f"session_{kind}",
                            "text": text,
                            "observedAt": observed_at,
                            "provenance": {
                                "path": str(rel),
                                "headingPath": ["sessions", obj.get("agentId") or "acp", kind],
                                "sessionKey": obj.get("childSessionKey") or obj.get("parentSessionKey"),
                            },
                        })
                        continue

                    if obj.get("type") != "message":
                        continue
                    observed_at = obj.get("timestamp")
                    if not within_range(observed_at, since, until):
                        continue
                    message = obj.get("message") or {}
                    role = message.get("role")
                    if role != "user":
                        continue
                    text = normalize_session_prompt_text(extract_message_text(message))
                    if not text or text == "NO_REPLY":
                        continue
                    items.append({
                        "id": f"session:{rel}:{obj.get('id') or observed_at}",
                        "kind": "session_prompt",
                        "text": text,
                        "observedAt": observed_at,
                        "provenance": {
                            "path": str(rel),
                            "headingPath": ["sessions", "prompt"],
                            "sessionKey": obj.get("sessionKey"),
                        },
                    })
        except OSError:
            continue
    return items


def score_item(item: dict[str, Any], query_tokens: list[str], args: argparse.Namespace) -> int:
    prov = item.get("provenance") or {}
    heading_path = " > ".join(prov.get("headingPath") or [])
    haystacks = [
        (item.get("text") or ""),
        prov.get("path") or "",
        heading_path,
        item.get("kind") or "",
        prov.get("repo") or "",
        prov.get("refs") or "",
    ]
    text_blob = "\n".join(haystacks).lower()

    if args.kind and item.get("kind") != args.kind:
        return 0
    if args.path and args.path.lower() not in (prov.get("path") or "").lower():
        return 0
    if args.heading and args.heading.lower() not in heading_path.lower():
        return 0

    observed_at = item.get("observedAt") or item.get("capturedAt") or ""
    if not within_range(observed_at, args.since, args.until):
        return 0

    score = 0
    for token in query_tokens:
        if token in text_blob:
            score += 3
        if token in heading_path.lower():
            score += 2
        if token in (prov.get("path") or "").lower():
            score += 2

    if args.mode_resolved == "activity":
        if item.get("kind") in {"git_commit", "session_system_event"}:
            score += 6
        elif item.get("kind") == "session_prompt":
            score += 1
        elif str(item.get("kind") or "").startswith("session_"):
            score += 3
        dt = parse_dt(observed_at)
        if dt:
            age_hours = max((datetime.now(timezone.utc) - dt).total_seconds() / 3600.0, 0)
            if age_hours <= 24:
                score += 4
            elif age_hours <= 72:
                score += 2
            elif age_hours <= 168:
                score += 1
        if is_activity_query(args.query) and not query_tokens:
            score += 2

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
        "repo": prov.get("repo"),
        "commit": prov.get("commit"),
        "sessionKey": prov.get("sessionKey"),
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
    ap.add_argument("--mode", choices=["auto", "evidence", "activity"], default="auto", help="Retrieval mode")
    ap.add_argument("--session-root", default="~/.openclaw/agents", help="OpenClaw agent/session root for activity mode")
    ap.add_argument("--git-max-depth", type=int, default=3, help="Max depth when discovering repos for activity mode")
    ap.add_argument("--json", action="store_true", help="Emit JSON")
    args = ap.parse_args()

    root = Path(args.root).expanduser().resolve()
    raw_dir = Path(args.raw).expanduser().resolve() if args.raw else (root / "raw")
    session_root = Path(args.session_root).expanduser().resolve()

    inferred_since, inferred_until, inferred = infer_time_bounds(args.query, args.since, args.until)
    if inferred_since and not args.since:
        args.since = inferred_since
    if inferred_until and not args.until:
        args.until = inferred_until

    if args.mode == "activity":
        args.mode_resolved = "activity"
    elif args.mode == "evidence":
        args.mode_resolved = "evidence"
    else:
        args.mode_resolved = "activity" if is_activity_query(args.query) else "evidence"

    query_tokens = tokenize(args.query)
    items = load_jsonl(raw_dir / "items.jsonl")
    source_counts: dict[str, int] = {"raw": len(items)}

    if args.mode_resolved == "activity":
        git_items = load_git_activity(root, args.since, args.until, max_depth=args.git_max_depth)
        session_items = load_session_activity(session_root, args.since, args.until)
        items.extend(git_items)
        items.extend(session_items)
        source_counts["git"] = len(git_items)
        source_counts["sessions"] = len(session_items)

    ranked: list[tuple[int, dict[str, Any]]] = []
    for item in items:
        score = score_item(item, query_tokens, args)
        if score > 0:
            ranked.append((score, item))
    ranked.sort(
        key=lambda x: (
            -x[0],
            -(parse_dt(x[1].get("observedAt") or x[1].get("capturedAt")) or datetime(1970, 1, 1, tzinfo=timezone.utc)).timestamp(),
            x[1].get("id") or "",
        )
    )

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
        "mode": args.mode_resolved,
        "raw": str(raw_dir),
        "since": args.since,
        "until": args.until,
        "sourceCounts": source_counts,
        "count": len(results),
        "results": results,
    }

    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    print("Mneme Retrieval")
    print("===============")
    print(f"query: {args.query}")
    print(f"mode: {args.mode_resolved}")
    if args.since:
        print(f"since: {args.since}")
    if args.until:
        print(f"until: {args.until}")
    print(f"results: {len(results)}")
    print()
    for idx, result in enumerate(results, start=1):
        cite = result["citation"]
        heading = " > ".join(cite["headingPath"])
        line_range = f"{cite['lineStart']}-{cite['lineEnd']}" if cite.get("lineStart") else "?"
        print(f"{idx}. [{result['score']}] {result['text']}")
        print(f"   citation: {cite['path']}:{line_range}")
        if cite.get("repo"):
            print(f"   repo: {cite['repo']}")
        if cite.get("commit"):
            print(f"   commit: {cite['commit']}")
        if cite.get("sessionKey"):
            print(f"   sessionKey: {cite['sessionKey']}")
        if heading:
            print(f"   heading: {heading}")
        if cite.get("observedAt"):
            print(f"   observedAt: {cite['observedAt']}")
        print(f"   evidence: {cite['evidenceItemId']}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
