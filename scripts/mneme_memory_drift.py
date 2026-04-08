#!/usr/bin/env python3
"""Detect likely contradictions, duplicates, and stale facts in OpenClaw memory files.

This is intentionally heuristic. It aims to surface review candidates, not to
pretend it knows final truth.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterable

FILE_DATE_RE = re.compile(r"(20\d{2}-\d{2}-\d{2})")

EXTRACTORS: list[tuple[str, re.Pattern[str]]] = [
    ("ash_ssh_port", re.compile(r"Ash(?:\s+SSH)?[^\n]*?port[^\d]*(\d{2,6})", re.I)),
    ("memory_provider", re.compile(r"memory search provider[^\n]*?(gemini|openai|voyage|mistral|local|ollama)", re.I)),
    ("default_model", re.compile(r"(?:default model|Current runtime default model|running on)[^`\n]*`?((?:openai-codex|anthropic|openai|google|gemini)[A-Za-z0-9._/-]+|GPT-[A-Za-z0-9._-]+|Opus\s*[0-9.]+|Sonnet\s*[0-9.]+)")),
    ("windows_mysql_port", re.compile(r"MySQL[^\n]{0,80}?port[^\d]*(\d{3,5})", re.I)),
    ("anima_protocol_version", re.compile(r"Anima Protocol v([0-9.]+)", re.I)),
    ("work_queue_stream", re.compile(r"Work queue stream[^`]*`([^`]+)`", re.I)),
    ("bdeep_checkout", re.compile(r"(?:Main checkout|real checkout)\s*:\s*`([^`]+)`", re.I)),
]

STALE_PATTERNS = [
    re.compile(r"\bcurrent state\b", re.I),
    re.compile(r"\bpending\b", re.I),
    re.compile(r"\bnot yet\b", re.I),
    re.compile(r"\btodo\b", re.I),
    re.compile(r"\bworking hypothesis\b", re.I),
    re.compile(r"\bactive\s+[—-]", re.I),
]

IGNORE_FILES = {
    "projects.md",
    "systems.md",
    "decisions.md",
    "incidents.md",
    "timeline.md",
}

SEVERITY_FOR_KEY = {
    "memory_provider": "high",
    "default_model": "high",
    "anima_protocol_version": "high",
    "work_queue_stream": "high",
    "ash_ssh_port": "medium",
    "windows_mysql_port": "medium",
    "bdeep_checkout": "medium",
}
SEVERITY_RANK = {"high": 3, "medium": 2, "low": 1}
CONFIDENCE_RANK = {"high": 3, "medium": 2, "low": 1}


@dataclass
class ExtractedFact:
    key: str
    value: str
    path: str
    line_no: int
    line: str


@dataclass
class StaleCandidate:
    path: str
    line_no: int
    age_days: int
    line: str
    reason: str
    severity: str
    confidence: str


@dataclass
class ContradictionCandidate:
    key: str
    values: dict[str, list[str]]
    severity: str
    confidence: str
    reason: str


@dataclass
class DuplicateCandidate:
    normalized: str
    refs: list[str]
    examples: list[str]
    severity: str
    confidence: str
    reason: str


def iter_files(root: Path) -> Iterable[Path]:
    memory_md = root / "MEMORY.md"
    if memory_md.exists():
        yield memory_md
    memdir = root / "memory"
    if memdir.exists():
        for path in sorted(memdir.glob("*.md")):
            if path.name in IGNORE_FILES:
                continue
            if path.name.endswith(".bak"):
                continue
            yield path


def relative(root: Path, path: Path) -> str:
    return str(path.relative_to(root))


def file_date(path: Path) -> date | None:
    m = FILE_DATE_RE.search(path.name)
    if not m:
        return None
    return datetime.strptime(m.group(1), "%Y-%m-%d").date()


def normalize_text(text: str) -> str:
    s = text.strip().lower()
    s = re.sub(r"^#{1,6}\s+", "", s)
    s = re.sub(r"^[-*+]\s+", "", s)
    s = s.replace("```", " ")
    s = re.sub(r"`([^`]+)`", r"\1", s)
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
    s = re.sub(r"__(.+?)__", r"\1", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def scan_facts(root: Path) -> list[ExtractedFact]:
    facts: list[ExtractedFact] = []
    for path in iter_files(root):
        for i, raw in enumerate(path.read_text(errors="replace").splitlines(), start=1):
            line = raw.strip()
            if not line:
                continue
            for key, pattern in EXTRACTORS:
                m = pattern.search(line)
                if m:
                    facts.append(ExtractedFact(key, m.group(1).strip(), relative(root, path), i, line))
    return facts


def contradiction_candidates(facts: list[ExtractedFact]) -> list[ContradictionCandidate]:
    grouped: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for fact in facts:
        grouped[fact.key][fact.value].append(f"{fact.path}:{fact.line_no}")
    out: list[ContradictionCandidate] = []
    for key, values in grouped.items():
        if len(values) <= 1:
            continue
        total_refs = sum(len(refs) for refs in values.values())
        severity = SEVERITY_FOR_KEY.get(key, "medium")
        confidence = "high" if total_refs >= 3 else "medium"
        reason = f"multiple distinct values found for structured fact `{key}`"
        out.append(ContradictionCandidate(key, dict(values), severity, confidence, reason))
    return sorted(out, key=lambda x: (-SEVERITY_RANK[x.severity], -CONFIDENCE_RANK[x.confidence], x.key))


def stale_candidates(root: Path, stale_days: int) -> list[StaleCandidate]:
    today = datetime.now(timezone.utc).date()
    out: list[StaleCandidate] = []
    for path in iter_files(root):
        pdate = file_date(path)
        age_days = (today - pdate).days if pdate else None
        for i, raw in enumerate(path.read_text(errors="replace").splitlines(), start=1):
            line = raw.strip()
            if not line:
                continue
            lower = line.lower()
            if "historical" in lower or "superseded" in lower:
                continue
            factish = line.startswith(("#", "-", "*")) or "todo" in lower or "pending" in lower or "current state" in lower
            if not factish:
                continue
            if age_days is not None and age_days >= stale_days:
                for pat in STALE_PATTERNS:
                    if pat.search(line):
                        severity = "high" if age_days >= max(stale_days * 4, 30) else "medium"
                        confidence = "high" if line.startswith(("-", "*", "#")) else "medium"
                        out.append(StaleCandidate(relative(root, path), i, age_days, line, f"old file + pattern {pat.pattern!r}", severity, confidence))
                        break
            elif path.name == "MEMORY.md":
                m = FILE_DATE_RE.search(line)
                if m:
                    d = datetime.strptime(m.group(1), "%Y-%m-%d").date()
                    line_age = (today - d).days
                    if line_age >= stale_days and any(p.search(line) for p in STALE_PATTERNS):
                        severity = "high" if line_age >= max(stale_days * 4, 30) else "medium"
                        out.append(StaleCandidate(relative(root, path), i, line_age, line, "dated line in MEMORY.md", severity, "medium"))
    return sorted(out, key=lambda x: (-SEVERITY_RANK[x.severity], -x.age_days, x.path, x.line_no))


def duplicate_candidates(root: Path) -> list[DuplicateCandidate]:
    grouped: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for path in iter_files(root):
        rel = relative(root, path)
        for i, raw in enumerate(path.read_text(errors="replace").splitlines(), start=1):
            line = raw.strip()
            if not line:
                continue
            if not line.startswith(("-", "*", "#")):
                continue
            norm = normalize_text(line)
            if len(norm) < 18:
                continue
            grouped[norm].append((f"{rel}:{i}", line))

    out: list[DuplicateCandidate] = []
    for norm, refs in grouped.items():
        unique_refs = [r for r, _ in refs]
        if len(unique_refs) < 2:
            continue
        distinct_files = {ref.split(":", 1)[0] for ref in unique_refs}
        if len(distinct_files) < 2:
            continue
        severity = "medium" if len(unique_refs) >= 3 else "low"
        confidence = "high" if len(unique_refs) >= 3 else "medium"
        out.append(DuplicateCandidate(
            normalized=norm,
            refs=unique_refs[:12],
            examples=[example for _ref, example in refs[:3]],
            severity=severity,
            confidence=confidence,
            reason="same normalized fact appears in multiple files",
        ))
    return sorted(out, key=lambda x: (-SEVERITY_RANK[x.severity], -CONFIDENCE_RANK[x.confidence], -len(x.refs), x.normalized))


def render_text(contradictions: list[ContradictionCandidate], stale: list[StaleCandidate], duplicates: list[DuplicateCandidate]) -> int:
    print("Mneme Memory Drift")
    print("==================")
    print(f"Contradiction candidates: {len(contradictions)}")
    print(f"Duplicate candidates: {len(duplicates)}")
    print(f"Stale candidates: {len(stale)}")
    print()

    if contradictions:
        print("## Contradiction candidates")
        for item in contradictions:
            print(f"- {item.key} [{item.severity}/{item.confidence}] {item.reason}")
            for value, refs in item.values.items():
                print(f"  - value: {value}")
                for ref in refs[:8]:
                    print(f"    - {ref}")
        print()

    if duplicates:
        print("## Duplicate clusters")
        for item in duplicates[:80]:
            print(f"- [{item.severity}/{item.confidence}] {item.examples[0]}")
            for ref in item.refs[:8]:
                print(f"  - {ref}")
        if len(duplicates) > 80:
            print(f"... {len(duplicates) - 80} more")
        print()

    if stale:
        print("## Stale candidates")
        for item in stale[:120]:
            print(f"- {item.path}:{item.line_no} ({item.age_days}d) [{item.severity}/{item.confidence}] {item.line}")
            print(f"  reason: {item.reason}")
        if len(stale) > 120:
            print(f"... {len(stale) - 120} more")

    return 1 if contradictions or stale or duplicates else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Detect likely contradictions and stale facts in memory files.")
    ap.add_argument("--root", default=".", help="Workspace root")
    ap.add_argument("--stale-days", type=int, default=7, help="Age threshold for stale candidate detection")
    ap.add_argument("--json", action="store_true", help="Emit JSON")
    args = ap.parse_args()

    root = Path(args.root).expanduser().resolve()
    facts = scan_facts(root)
    contradictions = contradiction_candidates(facts)
    stale = stale_candidates(root, args.stale_days)
    duplicates = duplicate_candidates(root)

    if args.json:
        print(json.dumps({
            "contradictions": [asdict(x) for x in contradictions],
            "duplicates": [asdict(x) for x in duplicates],
            "stale": [asdict(x) for x in stale],
            "counts": {"contradictions": len(contradictions), "duplicates": len(duplicates), "stale": len(stale)},
        }, indent=2))
        return 0

    return render_text(contradictions, stale, duplicates)


if __name__ == "__main__":
    raise SystemExit(main())
