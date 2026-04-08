#!/usr/bin/env python3
"""Scan OpenClaw memory files for likely secrets and optionally redact them.

Default mode is scan-only and prints redacted findings.
Apply mode rewrites files conservatively and creates .bak backups.
The review output is severity/confidence-ranked so obvious secrets surface first.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class PatternSpec:
    kind: str
    pattern: re.Pattern[str]
    replacement: str
    severity: str
    auto_apply: bool = True


PATTERNS: list[PatternSpec] = [
    PatternSpec("github_pat", re.compile(r"github_pat_[A-Za-z0-9_]+"), "github_pat_[REDACTED]", "critical"),
    PatternSpec("ghp", re.compile(r"ghp_[A-Za-z0-9_]+"), "ghp_[REDACTED]", "critical"),
    PatternSpec("glpat", re.compile(r"glpat-[A-Za-z0-9_\-]+"), "glpat-[REDACTED]", "critical"),
    PatternSpec("slack", re.compile(r"xox[baprs]-[A-Za-z0-9-]+"), "xox*-REDACTED", "critical"),
    PatternSpec("bearer", re.compile(r"(?i)(bearer\s+)([A-Za-z0-9._\-]+)"), r"\1[REDACTED]", "high"),
    PatternSpec("api_key", re.compile(r'''(?i)(api[_ -]?key\s*[:=]\s*["'`]?)(?!__OPENCLAW_REDACTED__)([^\s"'`,]+)'''), r"\1[REDACTED]", "critical"),
    PatternSpec("gateway_token", re.compile(r'''(?i)(gateway\s+token\s*[:=]\s*["'`]?)(?!__OPENCLAW_REDACTED__)([^\s"'`,]+)'''), r"\1[REDACTED]", "critical"),
    PatternSpec("token_field", re.compile(r'''(?i)(token\s*[:=]\s*["'`]?)(?!__OPENCLAW_REDACTED__)([^\s"'`,]+)'''), r"\1[REDACTED]", "medium", auto_apply=False),
    PatternSpec("password_field", re.compile(r'''(?i)(\bpass(word)?\b\s*[:=]\s*["'`]?)(?!<see\s)([^\s"'`,]+)'''), r"\1[REDACTED]", "high", auto_apply=False),
    PatternSpec("creds_pair", re.compile(r'''(?i)(creds?\s*[:=]\s*["'`]?)([^\n`]*?/[^\n`]+)'''), r"\1[REDACTED]", "high"),
    PatternSpec("rdp_pair", re.compile(r'''(?i)(rdp\s*:\s*["'`]?)([^\n`]*?/[^\n`]+)'''), r"\1[REDACTED]", "high"),
    PatternSpec("mysql_url", re.compile(r"mysql://[^\s)]+"), "mysql://[REDACTED]", "high"),
    PatternSpec("postgres_url", re.compile(r"postgres(ql)?://[^\s)]+"), "postgres://[REDACTED]", "high"),
]

ALLOWED_FILE_NAMES = {"MEMORY.md", "USER.md", "IDENTITY.md"}
SEVERITY_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1}
CONFIDENCE_RANK = {"high": 3, "medium": 2, "low": 1}
LOW_CONFIDENCE_LINE_HINTS = [
    re.compile(r"\bpass through\b", re.I),
    re.compile(r"\bpassing\b", re.I),
    re.compile(r"\bbypass\b", re.I),
    re.compile(r"\bcompass\b", re.I),
    re.compile(r"\bpasses\b", re.I),
]


@dataclass
class Finding:
    path: str
    line_no: int
    kind: str
    severity: str
    confidence: str
    reason: str
    line_redacted: str


def iter_files(root: Path) -> Iterable[Path]:
    for name in ALLOWED_FILE_NAMES:
        path = root / name
        if path.exists():
            yield path
    memdir = root / "memory"
    if memdir.exists():
        for path in sorted(memdir.glob("*.md")):
            if path.name.endswith(".bak"):
                continue
            yield path


def extract_secretish_value(match: re.Match[str]) -> str:
    for group in reversed(match.groups()):
        if group:
            return group.strip()
    return match.group(0).strip()


def confidence_for(spec: PatternSpec, line: str, match: re.Match[str]) -> tuple[str, str]:
    lowered = line.lower()
    secretish_value = extract_secretish_value(match)

    if any(p.search(line) for p in LOW_CONFIDENCE_LINE_HINTS):
        return "low", "looks like prose or a non-credential use of the word 'pass'"

    if spec.kind in {"github_pat", "ghp", "glpat", "slack", "gateway_token", "api_key", "mysql_url", "postgres_url", "creds_pair", "rdp_pair"}:
        return "high", "strong secret-specific pattern"

    if spec.kind == "bearer":
        if len(secretish_value) >= 12:
            return "high", "bearer token with credential-like length"
        return "medium", "bearer token pattern but short value"

    if spec.kind == "token_field":
        if len(secretish_value) >= 16 and re.search(r"[A-Z0-9_-]", secretish_value):
            return "high", "generic token field with credential-like value"
        if len(secretish_value) >= 8:
            return "medium", "generic token field with plausible secret value"
        return "low", "generic token label with a short or prose-like value"

    if spec.kind == "password_field":
        if len(secretish_value) >= 12 or re.search(r"\d", secretish_value) or re.search(r"[^A-Za-z]", secretish_value):
            return "high", "password field with credential-like value"
        if len(secretish_value) >= 6:
            return "medium", "password field but value could still be prose"
        return "low", "password/pass label with very short prose-like value"

    if "example" in lowered or "sample" in lowered:
        return "low", "looks like example/sample content"

    return "medium", "generic pattern match"


def scan_file(path: Path, root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for i, line in enumerate(path.read_text(errors="replace").splitlines(), start=1):
        for spec in PATTERNS:
            match = spec.pattern.search(line)
            if not match:
                continue
            confidence, reason = confidence_for(spec, line, match)
            findings.append(Finding(
                str(path.relative_to(root)),
                i,
                spec.kind,
                spec.severity,
                confidence,
                reason,
                spec.pattern.sub(spec.replacement, line).strip(),
            ))
            break
    return findings


def should_apply(spec: PatternSpec, apply_generic_fields: bool) -> bool:
    return spec.auto_apply or apply_generic_fields


def apply_file(path: Path, apply_generic_fields: bool) -> tuple[bool, int]:
    text = path.read_text(errors="replace")
    original = text
    changes = 0
    for spec in PATTERNS:
        if not should_apply(spec, apply_generic_fields):
            continue
        text, n = spec.pattern.subn(spec.replacement, text)
        changes += n
    if text != original:
        backup = path.with_suffix(path.suffix + ".bak")
        if not backup.exists():
            backup.write_text(original)
        path.write_text(text)
        return True, changes
    return False, 0


def build_summary(findings: list[Finding]) -> dict:
    severity_counts = Counter(f.severity for f in findings)
    confidence_counts = Counter(f.confidence for f in findings)
    by_kind = Counter(f.kind for f in findings)
    by_path: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "critical": 0, "high": 0, "medium": 0, "low": 0})
    for finding in findings:
        bucket = by_path[finding.path]
        bucket["total"] += 1
        bucket[finding.severity] += 1
    return {
        "severity": dict(severity_counts),
        "confidence": dict(confidence_counts),
        "kinds": dict(by_kind),
        "paths": dict(sorted(by_path.items())),
    }


def sorted_findings(findings: list[Finding]) -> list[Finding]:
    return sorted(
        findings,
        key=lambda f: (
            -SEVERITY_RANK[f.severity],
            -CONFIDENCE_RANK[f.confidence],
            f.path,
            f.line_no,
        ),
    )


def print_bucket(title: str, findings: list[Finding]) -> None:
    if not findings:
        return
    print(title)
    for f in findings[:120]:
        print(f"- {f.path}:{f.line_no} [{f.severity}/{f.confidence} {f.kind}] {f.line_redacted}")
        print(f"  reason: {f.reason}")
    if len(findings) > 120:
        print(f"... {len(findings) - 120} more")
    print()


def main() -> int:
    ap = argparse.ArgumentParser(description="Scan or redact secrets in OpenClaw memory files.")
    ap.add_argument("--root", default=".", help="Workspace root")
    ap.add_argument("--apply", action="store_true", help="Rewrite files in place and create .bak backups")
    ap.add_argument("--apply-generic-fields", action="store_true", help="Also rewrite generic token/password fields during --apply")
    ap.add_argument("--json", action="store_true", help="Emit JSON")
    args = ap.parse_args()

    root = Path(args.root).expanduser().resolve()
    findings: list[Finding] = []
    changed: list[dict] = []

    for path in iter_files(root):
        findings.extend(scan_file(path, root))

    findings = sorted_findings(findings)
    summary = build_summary(findings)

    if args.apply:
        touched = sorted({f.path for f in findings})
        for rel in touched:
            changed_flag, count = apply_file(root / rel, args.apply_generic_fields)
            if changed_flag:
                changed.append({"path": rel, "replacements": count})

    if args.json:
        print(json.dumps({
            "findings": [f.__dict__ for f in findings],
            "summary": summary,
            "changed": changed,
            "total_findings": len(findings),
        }, indent=2))
        return 0

    print("Mneme Secret Scrub")
    print("==================")
    print(f"Findings: {len(findings)}")
    sev = summary["severity"]
    conf = summary["confidence"]
    if findings:
        print(
            "Severity: "
            f"critical={sev.get('critical', 0)} high={sev.get('high', 0)} "
            f"medium={sev.get('medium', 0)} low={sev.get('low', 0)}"
        )
        print(
            "Confidence: "
            f"high={conf.get('high', 0)} medium={conf.get('medium', 0)} low={conf.get('low', 0)}"
        )
        print()

        print_bucket("## Highest priority", [f for f in findings if f.severity in {"critical", "high"} and f.confidence == "high"])
        print_bucket("## Needs review", [f for f in findings if f.confidence == "medium"])
        print_bucket("## Likely false positives / low-confidence", [f for f in findings if f.confidence == "low"])

        print("## Files worth checking first")
        hot_paths = sorted(summary["paths"].items(), key=lambda item: (-item[1]["critical"], -item[1]["high"], -item[1]["total"], item[0]))
        for path, counts in hot_paths[:25]:
            print(f"- {path}: total={counts['total']} critical={counts['critical']} high={counts['high']} medium={counts['medium']} low={counts['low']}")
        print()

    if args.apply:
        print("Applied changes:")
        if changed:
            for item in changed:
                print(f"- {item['path']} ({item['replacements']} replacements)")
            if not args.apply_generic_fields:
                print("- generic token/password field rewrites were skipped unless you pass --apply-generic-fields")
        else:
            print("- no files changed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
