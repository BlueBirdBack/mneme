#!/usr/bin/env python3
"""Compile Mneme raw evidence into a first-pass compiled memory pack.

Primary input:
- raw/sources.jsonl
- raw/items.jsonl

Legacy fallback:
- direct markdown parsing from MEMORY.md + memory/*.md

Outputs:
- compiled/documents.jsonl
- compiled/entries.jsonl
- rendered markdown views

This version intentionally favors quality over recall volume:
- heading-only lines are dropped from compiled entries
- low-value project noise is suppressed
- timeline events are deduplicated more aggressively
- bucket classification uses stronger heading-aware routing
- people/profile material gets its own bucket instead of leaking into project/system noise
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

CATEGORY_CONFIG = {
    "projects": {
        "include": [
            r"\bproject\b", r"\brepo\b", r"\bdeploy\b", r"\bworktree\b", r"\bcheckout\b",
            r"\bdemo\b", r"\bfrontend\b", r"\bbaseurl\b", r"\blive\b", r"\bmap\b",
            r"\bgeo\b", r"\btruth layer\b", r"\betl\b", r"\bcurat(ed|ion)\b",
            r"\btag correction\b", r"\bpositioning\b",
        ],
        "exclude": [
            r"\bnats\b", r"\bmysql\b", r"\bmqtt\b", r"\bssh\b", r"\bgateway\b",
            r"\btoken\b", r"\bcert\b", r"\bapi key\b", r"\bservice(s)?\b",
            r"\btimezone\b", r"\bpronouns?\b", r"\bwhat to call\b",
        ],
        "headingHints": [r"active projects", r"durable project facts", r"bdeep", r"yibin", r"aqua", r"mneme"],
    },
    "systems": {
        "include": [
            r"\bhost\b", r"\bserver\b", r"\bssh\b", r"\bgateway\b", r"\bnats\b",
            r"\bmemory\b", r"\bmysql\b", r"\bmqtt\b", r"\bforgejo\b", r"\bapi\b",
            r"\bservice(s)?\b", r"\bwebsocket\b", r"\btunnel\b", r"\bcert\b", r"\bport\b",
            r"\bendpoint\b", r"\bcluster\b", r"\bcontainer\b", r"\bdocker\b",
        ],
        "exclude": [
            r"\bbounty\b", r"\bissue\b", r"\bprefers\b", r"\bavoid\b", r"\bno public\b",
            r"\bproof summaries\b", r"\bdecision support\b",
        ],
        "headingHints": [r"systems", r"infrastructure", r"key infrastructure", r"access", r"memory stack"],
    },
    "decisions": {
        "include": [
            r"\bdecision\b", r"\bhard rule\b", r"\bdo not\b", r"\bmust\b", r"\bshould\b",
            r"\bprefer\b", r"\brule\b", r"\bpolicy\b", r"\bchosen\b", r"\bkeep\b",
            r"\bavoid\b", r"\bno public\b", r"\bprimary target\b", r"\bintentional\b",
            r"\btruth layer\b", r"\bmap is the primary target\b",
        ],
        "exclude": [
            r"\boutage\b", r"\bfailed\b", r"\bmysql\b", r"\bmqtt\b", r"\bssh port\b",
            r"\bhost\b\s*:\s*`?\d", r"\bserver\b\s*is\s*\d", r"\bcommit\b", r"\bmedia attached\b",
            r"\bpending\b",
        ],
        "headingHints": [r"decisions", r"preferences", r"methods", r"hard constraints"],
    },
    "incidents": {
        "include": [
            r"\bincident\b", r"\broot cause\b", r"\boutage\b", r"\bfailed\b", r"\bbroken\b",
            r"\bcompromise\b", r"\bspike\b", r"\bcpu\b", r"\bram\b", r"\bfix\b",
            r"\brecovered\b", r"\bdelay\b", r"\bgarbl(ed|ing)\b", r"\bbug\b",
            r"\bmemory search\b.*\bunavailable\b", r"\bwrong path\b",
        ],
        "exclude": [r"\bprefer left alignment\b", r"\bproof summaries\b", r"\bcommit\b", r"\bpending\b", r"\bhistorical\b"],
        "headingHints": [r"incidents", r"warnings", r"alert", r"postmortem"],
    },
    "people": {
        "include": [
            r"\bname\b", r"\bwhat to call\b", r"\bpronouns?\b", r"\btimezone\b", r"\bvibe\b",
            r"\bcreature\b", r"\bemoji\b", r"\bavatar\b", r"\bbruce bell\b",
            r"\buser\b.*\bname\b", r"\bcall them\b", r"\bprefers\b.*\breplies\b",
            r"\bfrontend architect\b", r"\bhust\b", r"\bsoftware\b",
        ],
        "exclude": [
            r"\bproject\b", r"\bmysql\b", r"\bmqtt\b", r"\bforgejo\b", r"\bnats\b",
            r"\bservice(s)?\b", r"\bdeploy\b", r"\bincident\b", r"\bhost\b", r"\bssh\b",
            r"\bgateway\b", r"\bmemory search\b", r"\bsudo\b", r"\bmodel\b", r"\bcreds?\b",
        ],
        "headingHints": [r"identity", r"user", r"people", r"profile"],
    },
}

CATEGORY_PRIORITY = {"incidents": 5, "decisions": 4, "systems": 3, "projects": 2, "people": 1}
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
HEADING_BUCKET_HINTS = {
    "projects": [r"active projects", r"durable project facts", r"bdeep", r"yibin", r"aqua", r"mneme"],
    "systems": [r"key infrastructure", r"systems", r"access", r"memory stack"],
    "decisions": [r"durable decisions", r"preferences", r"methods", r"hard constraints"],
    "incidents": [r"incidents", r"warnings"],
    "people": [r"identity", r"user", r"people", r"profile"],
}

SECRET_PATTERNS = [
    (re.compile(r"ghp_[A-Za-z0-9_]+"), "ghp_[REDACTED]"),
    (re.compile(r"(token\s*[:=]\s*)([^\s,`]+)", re.I), r"\1[REDACTED]"),
    (re.compile(r"(api[_-]?key\s*[:=]\s*)([^\s,`]+)", re.I), r"\1[REDACTED]"),
    (re.compile(r"(pass(word)?\s*[:=]\s*)([^\s,`]+)", re.I), r"\1[REDACTED]"),
]

IGNORE_MEMORY_FILES = {"projects.md", "systems.md", "decisions.md", "incidents.md", "timeline.md", "people.md"}
GENERIC_TITLES = {
    "conversation summary", "source files", "sources", "tools", "methods", "pending",
    "what it does", "what it is", "what it is not", "goal", "status",
    "current status", "stable assumptions", "recommended next step", "practical interpretation",
    "docs", "automation", "runtime orchestration", "continuation guide",
}
LOW_VALUE_PATTERNS = [
    re.compile(r"\bTODO\b", re.I),
    re.compile(r"\bpending\b", re.I),
    re.compile(r"\bblocked\b", re.I),
    re.compile(r"\bbranch\b\s+[`\w/-]+", re.I),
    re.compile(r"\bcommit\b\s+[0-9a-f]{7,40}\b", re.I),
    re.compile(r"\b[0-9a-f]{7,40}\b"),
    re.compile(r"\bPR\s*#\d+\b", re.I),
    re.compile(r"\bissue\s*#\d+\b", re.I),
    re.compile(r"sender_label|message_id|timestamp|untrusted metadata", re.I),
    re.compile(r"^(assistant|user):", re.I),
    re.compile(r"\bconversation info\b", re.I),
    re.compile(r"\[media attached:", re.I),
    re.compile(r"new session started", re.I),
    re.compile(r"^```"),
]


@dataclass
class SourceLine:
    file: str
    line_no: int
    text: str
    evidence_id: str | None = None
    observed_at: str | None = None
    heading_path: list[str] = field(default_factory=list)
    kind: str | None = None


def redact(text: str) -> str:
    out = text
    for pattern, repl in SECRET_PATTERNS:
        out = pattern.sub(repl, out)
    return out


def slugify(text: str, limit: int = 48) -> str:
    s = text.lower()
    s = re.sub(r"[`*_#\[\](){}:;,.!?]+", " ", s)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:limit] or "entry"


def clean_markdown_text(text: str) -> str:
    s = text.strip()
    s = re.sub(r"^#{1,6}\s+", "", s)
    s = re.sub(r"^[-*+]\s+", "", s)
    s = re.sub(r"^>\s+", "", s)
    s = s.replace("```", " ")
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
    s = re.sub(r"__(.+?)__", r"\1", s)
    s = re.sub(r"`([^`]+)`", r"\1", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def summarize(text: str, limit: int = 180) -> str:
    s = clean_markdown_text(text)
    return s if len(s) <= limit else s[: limit - 1].rstrip() + "…"


def normalize_title(text: str) -> str:
    s = summarize(text, 120).lower()
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    return s


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(errors="replace").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def source_files(root: Path) -> list[Path]:
    files: list[Path] = []
    memory_md = root / "MEMORY.md"
    if memory_md.exists():
        files.append(memory_md)
    memory_dir = root / "memory"
    if memory_dir.exists():
        for path in sorted(memory_dir.glob("*.md")):
            if path.name in IGNORE_MEMORY_FILES or path.name.endswith((".bak", "-memory-pre-trim.md")):
                continue
            files.append(path)
    return files


def heading_path_from_lines(lines: list[tuple[int, str]], current_index: int) -> list[str]:
    path: list[tuple[int, str]] = []
    for i, line in lines:
        if i >= current_index:
            break
        stripped = line.strip()
        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            title = stripped[level:].strip()
            path = [x for x in path if x[0] < level]
            path.append((level, title))
    return [title for _level, title in path]


def iter_candidate_lines(path: Path, root: Path) -> Iterable[SourceLine]:
    lines = [(i, raw.rstrip()) for i, raw in enumerate(path.read_text(errors="replace").splitlines(), start=1)]
    for i, raw in lines:
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#") or line.startswith("-") or line.startswith("*"):
            yield SourceLine(
                file=str(path.relative_to(root)),
                line_no=i,
                text=redact(line),
                heading_path=heading_path_from_lines(lines, i),
                kind="memory_line",
            )


def is_heading_only_text(text: str) -> bool:
    stripped = text.strip()
    if not stripped.startswith("#"):
        return False
    lines = [ln.strip() for ln in stripped.splitlines() if ln.strip()]
    return len(lines) == 1


def body_lines(text: str) -> list[str]:
    out: list[str] = []
    for ln in text.splitlines():
        s = ln.strip()
        if not s or s.startswith("#") or s.startswith("```"):
            continue
        cleaned = clean_markdown_text(s)
        if cleaned:
            out.append(cleaned)
    return out


def first_body_line(text: str) -> str:
    lines = body_lines(text)
    if lines:
        return lines[0]
    cleaned = clean_markdown_text(text)
    return cleaned


def is_generic_or_noise_title(text: str) -> bool:
    norm = normalize_title(text)
    if not norm:
        return True
    if norm in GENERIC_TITLES:
        return True
    if re.fullmatch(r"20\d{2} \d{2} \d{2}", norm):
        return True
    return False


def is_low_value_noise(text: str) -> bool:
    return any(p.search(text) for p in LOW_VALUE_PATTERNS)


def is_low_value_item(item: SourceLine, category: str | None = None) -> bool:
    text = item.text.strip()
    if not text:
        return True
    if is_heading_only_text(text):
        return True
    if item.kind == "note_section" and not body_lines(text):
        return True
    body = first_body_line(text)
    if is_generic_or_noise_title(body):
        return True
    if is_low_value_noise(text):
        return True
    return False


def heading_bucket(item: SourceLine) -> tuple[str | None, int]:
    heading_text = " > ".join(item.heading_path).lower()
    best = None
    score = 0
    for category, pats in HEADING_BUCKET_HINTS.items():
        s = sum(1 for pat in pats if re.search(pat, heading_text))
        if s > score:
            best, score = category, s
    return best, score


def score_category(item: SourceLine, category: str) -> int:
    cfg = CATEGORY_CONFIG[category]
    text = item.text.lower()
    body = first_body_line(item.text).lower()
    heading_text = " > ".join(item.heading_path).lower()
    score = 0
    for pat in cfg["include"]:
        if re.search(pat, text) or re.search(pat, body):
            score += 2
    for pat in cfg.get("headingHints", []):
        if re.search(pat, heading_text):
            score += 1
    hinted_category, hinted_score = heading_bucket(item)
    if hinted_category == category and hinted_score > 0:
        score += min(hinted_score, 2)
    for pat in cfg.get("exclude", []):
        if re.search(pat, text) or re.search(pat, body):
            score -= 2
    return score


def classify_item(item: SourceLine) -> str | None:
    if is_low_value_item(item):
        return None
    scores: dict[str, int] = {category: score_category(item, category) for category in CATEGORY_CONFIG}
    best_category = None
    best_score = 0
    for category, score in scores.items():
        if score > best_score or (score == best_score and score > 0 and best_category and CATEGORY_PRIORITY[category] > CATEGORY_PRIORITY[best_category]):
            best_category = category
            best_score = score
    if best_score <= 0:
        return None
    if best_category == "people" and best_score < 3:
        return None
    if best_category in {"incidents", "decisions"} and scores.get("projects", 0) >= best_score and scores.get("projects", 0) > 0:
        best_category = "projects"
    if is_low_value_item(item, best_category):
        return None
    return best_category


def extract_section_title(item: SourceLine) -> str | None:
    lines = [ln.strip() for ln in item.text.splitlines() if ln.strip()]
    if not lines:
        return None
    if lines[0].startswith("#"):
        level = len(lines[0]) - len(lines[0].lstrip("#"))
        title = lines[0][level:].strip()
        return title or None
    if item.heading_path:
        return item.heading_path[-1]
    return None


def collect_legacy(root: Path) -> tuple[dict[str, list[SourceLine]], list[str], list[tuple[str, str, str, int | None, str | None]]]:
    collected = {k: [] for k in CATEGORY_CONFIG}
    files = source_files(root)
    sources = [str(p.relative_to(root)) for p in files]
    timeline: list[tuple[str, str, str, int | None, str | None]] = []
    date_re = re.compile(r"(20\d{2}-\d{2}-\d{2})")
    for path in files:
        rel = str(path.relative_to(root))
        for item in iter_candidate_lines(path, root):
            category = classify_item(item)
            if category:
                collected[category].append(item)
            title = extract_section_title(item)
            if item.kind == "memory_line" and title and not is_generic_or_noise_title(title):
                m = date_re.search(rel)
                date_key = m.group(1) if m else "undated"
                timeline.append((date_key, title, rel, item.line_no, None))
    return collected, sources, timeline


def collect_from_raw(raw_dir: Path) -> tuple[dict[str, list[SourceLine]], list[str], list[tuple[str, str, str, int | None, str | None]]]:
    sources_rows = load_jsonl(raw_dir / "sources.jsonl")
    items_rows = load_jsonl(raw_dir / "items.jsonl")
    if not sources_rows or not items_rows:
        raise FileNotFoundError(f"Missing raw Mneme evidence in {raw_dir}")

    sources = [row.get("workspacePath") or row.get("uri") or row.get("id") for row in sources_rows]
    collected = {k: [] for k in CATEGORY_CONFIG}
    timeline: list[tuple[str, str, str, int | None, str | None]] = []

    for item in items_rows:
        text = redact(item.get("text", "").strip())
        if not text:
            continue
        prov = item.get("provenance", {})
        rel = prov.get("path") or item.get("sourceId") or "unknown"
        line_no = int(prov.get("lineStart") or 0)
        observed = item.get("observedAt")
        candidate = SourceLine(
            file=rel,
            line_no=line_no,
            text=text,
            evidence_id=item.get("id"),
            observed_at=observed,
            heading_path=list(prov.get("headingPath") or []),
            kind=item.get("kind"),
        )
        category = classify_item(candidate)
        if category:
            collected[category].append(candidate)
        if item.get("kind") == "note_section":
            title = extract_section_title(candidate)
            if title and not is_generic_or_noise_title(title):
                date_key = observed[:10] if observed else "undated"
                timeline.append((date_key, title, rel, line_no if line_no else None, item.get("id")))

    return collected, sources, timeline


def unique_lines(items: list[SourceLine], limit: int = 80) -> list[SourceLine]:
    seen: set[str] = set()
    out: list[SourceLine] = []
    for item in items:
        key = normalize_title(first_body_line(item.text))
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(item)
        if len(out) >= limit:
            break
    return out


def dedupe_timeline(entries: list[tuple[str, str, str, int | None, str | None]]) -> list[tuple[str, str, str, int | None, str | None]]:
    out: list[tuple[str, str, str, int | None, str | None]] = []
    seen_same_day: set[tuple[str, str]] = set()
    last_key = None
    for date_key, title, rel, line_no, evidence_id in sorted(entries):
        norm = normalize_title(title)
        key = (date_key, norm)
        if key == last_key or key in seen_same_day:
            continue
        seen_same_day.add(key)
        out.append((date_key, title, rel, line_no, evidence_id))
        last_key = key
    return out[:200]


def evidence_refs(item: SourceLine) -> list[dict[str, Any]]:
    if item.evidence_id:
        return [{"evidenceItemId": item.evidence_id}]
    return [{"evidenceItemId": f"legacy:{item.file}:{item.line_no}"}]


def build_compiled_document(kind: str, entry_ids: list[str], sources: list[str], generated_at: str) -> dict[str, Any]:
    return {
        "id": f"doc:compiled:{kind}",
        "kind": kind,
        "title": DOCUMENT_TITLES[kind],
        "generatedAt": generated_at,
        "entryIds": entry_ids,
        "sourceIds": sources,
    }


def heading_context(item: SourceLine) -> str | None:
    for heading in reversed(item.heading_path):
        cleaned = summarize(heading, 80)
        if cleaned and not is_generic_or_noise_title(cleaned):
            return cleaned
    return None


def title_for_item(item: SourceLine) -> str:
    if item.kind == "note_section":
        section_title = extract_section_title(item)
        if section_title and not is_generic_or_noise_title(section_title):
            return summarize(section_title, 96)

    line = first_body_line(item.text)
    match = re.match(r"^([^:：]{1,48})[:：]\s+(.+)$", line)
    if match:
        label = summarize(match.group(1), 48)
        if label and not is_generic_or_noise_title(label):
            context = heading_context(item)
            if context and normalize_title(context) != normalize_title(label):
                return summarize(f"{context} — {label}", 96)
            return summarize(label, 96)

    return summarize(line, 96)


def summary_for_item(item: SourceLine) -> str:
    lines = body_lines(item.text)
    if not lines:
        return summarize(item.text, 220)
    joined = " ".join(lines)
    return summarize(joined, 220)


def build_compiled_entries(kind: str, items: list[SourceLine], document_id: str, generated_at: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for idx, item in enumerate(items, start=1):
        title = title_for_item(item)
        entry_id = f"cmp:{ENTRY_TYPES[kind]}:{slugify(title)}-{idx:03d}"
        entry = {
            "id": entry_id,
            "documentId": document_id,
            "entryType": ENTRY_TYPES[kind],
            "title": title,
            "summary": summary_for_item(item),
            "state": "observed",
            "updatedAt": generated_at,
            "tags": [kind.rstrip("s"), "compiled"],
            "facts": [{"key": "sourceLine", "value": item.text, "state": "observed", "evidenceRefs": evidence_refs(item)}],
            "relations": [],
            "evidenceRefs": evidence_refs(item),
            "meta": {"sourcePath": item.file, "lineNo": item.line_no, "headingPath": item.heading_path},
        }
        if item.observed_at:
            entry["observedAt"] = item.observed_at
            entry["lastConfirmedAt"] = item.observed_at
        out.append(entry)
    return out


def build_timeline_entries(entries: list[tuple[str, str, str, int | None, str | None]], generated_at: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for idx, (date_key, title, rel, line_no, evidence_id) in enumerate(entries, start=1):
        entry_id = f"cmp:timeline:{date_key}:{slugify(title)}-{idx:03d}"
        refs = [{"evidenceItemId": evidence_id}] if evidence_id else [{"evidenceItemId": f"legacy:{rel}:{line_no or 0}"}]
        entry = {
            "id": entry_id,
            "documentId": "doc:compiled:timeline",
            "entryType": "timeline_event",
            "title": title,
            "summary": title,
            "state": "historical",
            "updatedAt": generated_at,
            "tags": ["timeline", "compiled"],
            "facts": [],
            "relations": [],
            "evidenceRefs": refs,
            "meta": {"sourcePath": rel, "lineNo": line_no, "dateKey": date_key},
        }
        if re.match(r"20\d{2}-\d{2}-\d{2}", date_key):
            entry["observedAt"] = f"{date_key}T00:00:00Z"
            entry["lastConfirmedAt"] = f"{date_key}T00:00:00Z"
        out.append(entry)
    return out


def write_category_markdown(path: Path, title: str, entries: list[dict[str, Any]], sources: list[str], mode: str) -> None:
    lines = [f"# Compiled Memory — {title}", "", f"> Generated by `scripts/mneme_compile_memory.py` from **{mode}** input. Review before treating as truth.", ""]
    if entries:
        for entry in entries:
            lines += [f"## {entry['title']}", "", entry['summary'], "", f"- Entry: `{entry['id']}`", f"- State: `{entry['state']}`", f"- Facts: {len(entry.get('facts', []))}"]
            for fact in entry.get('facts', [])[:6]:
                lines.append(f"  - {fact['value']}")
            if len(entry.get('facts', [])) > 6:
                lines.append(f"  - … {len(entry['facts']) - 6} more")
            lines.append("")
    else:
        lines += ["## Candidate facts", "", "- No candidate facts found in this pass.", ""]
    lines += ["## Sources", *[f"- `{s}`" for s in sources], ""]
    path.write_text("\n".join(lines))


def write_timeline_markdown(out_path: Path, entries: list[tuple[str, str, str, int | None, str | None]], sources: list[str], mode: str, timeline_entries: list[dict[str, Any]]) -> None:
    lines = ["# Compiled Memory — Timeline", "", f"> Generated by `scripts/mneme_compile_memory.py` from **{mode}** input. Review before treating as truth.", ""]
    if entries:
        current = None
        for (date_key, title, rel, line_no, _), entry in zip(entries, timeline_entries):
            if date_key != current:
                lines.append(f"## {date_key}")
                current = date_key
            lines.append(f"- {title}  ")
            lines.append(f"  Source: `{rel}`")
            lines.append(f"  Entry: `{entry['id']}`")
            if line_no:
                lines.append(f"  Line: `{line_no}`")
    else:
        lines.append("- No timeline entries found.")
    lines += ["", "## Sources", *[f"- `{s}`" for s in sources], ""]
    out_path.write_text("\n".join(lines))


def build_report(out_dir: Path, sources: list[str], collected: dict[str, list[SourceLine]], mode: str, raw_dir: str | None, document_count: int, entry_count: int) -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = ["# Mneme Compile Report", "", f"Generated: {now}", f"Mode: {mode}"]
    if raw_dir:
        lines.append(f"Raw input: `{raw_dir}`")
    lines += ["", "## Inputs", *[f"- `{s}`" for s in sources], "", "## Candidate counts"]
    for category, items in collected.items():
        lines.append(f"- {category}: {len(unique_lines(items))}")
    lines += [f"- documents: {document_count}", f"- entries: {entry_count}", "", "## Notes", "- Heading-only lines are suppressed.", "- Low-value project noise is filtered.", "- Timeline events are deduplicated by day/title.", "- Bucket classification is heading-aware and includes a people/profile lane.", ""]
    (out_dir / "report.md").write_text("\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a first-pass compiled memory pack.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--out", default="compiled")
    parser.add_argument("--raw", default=None)
    parser.add_argument("--legacy-direct", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    out_dir = Path(args.out).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    mode = "legacy-direct"
    raw_dir = None
    if args.legacy_direct:
        collected, sources, timeline = collect_legacy(root)
    else:
        raw_candidate = Path(args.raw).expanduser().resolve() if args.raw else (root / "raw")
        try:
            collected, sources, timeline = collect_from_raw(raw_candidate)
            mode = "raw-evidence"
            raw_dir = str(raw_candidate)
        except FileNotFoundError:
            collected, sources, timeline = collect_legacy(root)

    timeline = dedupe_timeline(timeline)
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    documents: list[dict[str, Any]] = []
    entries_json: list[dict[str, Any]] = []
    for kind in ("projects", "systems", "decisions", "incidents", "people"):
        uniq = unique_lines(collected[kind])
        doc_id = f"doc:compiled:{kind}"
        entries = build_compiled_entries(kind, uniq, doc_id, generated_at)
        documents.append(build_compiled_document(kind, [e['id'] for e in entries], sources, generated_at))
        entries_json.extend(entries)
        write_category_markdown(out_dir / f"{kind}.md", kind.title(), entries, sources, mode)

    timeline_entries = build_timeline_entries(timeline, generated_at)
    documents.append(build_compiled_document("timeline", [e['id'] for e in timeline_entries], sources, generated_at))
    entries_json.extend(timeline_entries)
    write_timeline_markdown(out_dir / "timeline.md", timeline, sources, mode, timeline_entries)

    write_jsonl(out_dir / "documents.jsonl", documents)
    write_jsonl(out_dir / "entries.jsonl", entries_json)
    build_report(out_dir, sources, collected, mode, raw_dir, len(documents), len(entries_json))
    print(f"Compiled memory pack written to {out_dir} (mode={mode}, documents={len(documents)}, entries={len(entries_json)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
