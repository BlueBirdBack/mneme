#!/usr/bin/env python3
"""Scan OpenClaw memory files for likely secrets and optionally redact them.

Default mode is scan-only and prints redacted findings.
Apply mode rewrites files conservatively and creates .bak backups.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    ("github_pat", re.compile(r"github_pat_[A-Za-z0-9_]+"), "github_pat_[REDACTED]"),
    ("ghp", re.compile(r"ghp_[A-Za-z0-9_]+"), "ghp_[REDACTED]"),
    ("glpat", re.compile(r"glpat-[A-Za-z0-9_\-]+"), "glpat-[REDACTED]"),
    ("slack", re.compile(r"xox[baprs]-[A-Za-z0-9-]+"), "xox*-REDACTED"),
    ("bearer", re.compile(r"(?i)(bearer\s+)([A-Za-z0-9._\-]+)"), r"\1[REDACTED]"),
    ("api_key", re.compile(r'''(?i)(api[_ -]?key\s*[:=]\s*["'`]?)(?!__OPENCLAW_REDACTED__)([^\s"'`,]+)'''), r"\1[REDACTED]"),
    ("gateway_token", re.compile(r'''(?i)(gateway\s+token\s*[:=]\s*["'`]?)(?!__OPENCLAW_REDACTED__)([^\s"'`,]+)'''), r"\1[REDACTED]"),
    ("token_field", re.compile(r'''(?i)(token\s*[:=]\s*["'`]?)(?!__OPENCLAW_REDACTED__)([^\s"'`,]+)'''), r"\1[REDACTED]"),
    ("password_field", re.compile(r'''(?i)(pass(word)?\s*[:=]\s*["'`]?)(?!<see\s)([^\s"'`,]+)'''), r"\1[REDACTED]"),
    ("creds_pair", re.compile(r'''(?i)(creds?\s*[:=]\s*["'`]?)([^\n`]*?/[^\n`]+)'''), r"\1[REDACTED]"),
    ("rdp_pair", re.compile(r'''(?i)(rdp\s*:\s*["'`]?)([^\n`]*?/[^\n`]+)'''), r"\1[REDACTED]"),
    ("mysql_url", re.compile(r"mysql://[^\s)]+"), "mysql://[REDACTED]"),
    ("postgres_url", re.compile(r"postgres(ql)?://[^\s)]+"), "postgres://[REDACTED]"),
]

ALLOWED_FILE_NAMES = {"MEMORY.md", "USER.md", "IDENTITY.md"}


@dataclass
class Finding:
    path: str
    line_no: int
    kind: str
    line_redacted: str


def iter_files(root: Path) -> Iterable[Path]:
    for name in ALLOWED_FILE_NAMES:
        path = root / name
        if path.exists():
            yield path
    memdir = root / "memory"
    if memdir.exists():
        for path in sorted(memdir.glob("*.md")):
            yield path


def scan_file(path: Path, root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for i, line in enumerate(path.read_text(errors="replace").splitlines(), start=1):
        for kind, pattern, repl in PATTERNS:
            if pattern.search(line):
                findings.append(Finding(str(path.relative_to(root)), i, kind, pattern.sub(repl, line).strip()))
                break
    return findings


def apply_file(path: Path) -> tuple[bool, int]:
    text = path.read_text(errors="replace")
    original = text
    changes = 0
    for _kind, pattern, repl in PATTERNS:
        text, n = pattern.subn(repl, text)
        changes += n
    if text != original:
        backup = path.with_suffix(path.suffix + ".bak")
        if not backup.exists():
            backup.write_text(original)
        path.write_text(text)
        return True, changes
    return False, 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Scan or redact secrets in OpenClaw memory files.")
    ap.add_argument("--root", default=".", help="Workspace root")
    ap.add_argument("--apply", action="store_true", help="Rewrite files in place and create .bak backups")
    ap.add_argument("--json", action="store_true", help="Emit JSON")
    args = ap.parse_args()

    root = Path(args.root).expanduser().resolve()
    findings: list[Finding] = []
    changed: list[dict] = []

    for path in iter_files(root):
        findings.extend(scan_file(path, root))

    if args.apply:
        touched = sorted({f.path for f in findings})
        for rel in touched:
            changed_flag, count = apply_file(root / rel)
            if changed_flag:
                changed.append({"path": rel, "replacements": count})

    if args.json:
        print(json.dumps({
            "findings": [f.__dict__ for f in findings],
            "changed": changed,
            "total_findings": len(findings),
        }, indent=2))
        return 0

    print("Mneme Secret Scrub")
    print("==================")
    print(f"Findings: {len(findings)}")
    if findings:
        for f in findings[:200]:
            print(f"- {f.path}:{f.line_no} [{f.kind}] {f.line_redacted}")
        if len(findings) > 200:
            print(f"... {len(findings) - 200} more")
    if args.apply:
        print("\nApplied changes:")
        for item in changed:
            print(f"- {item['path']} ({item['replacements']} replacements)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
