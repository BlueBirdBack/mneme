#!/usr/bin/env python3
"""Run the Mneme maintenance flow.

Default flow:
1. memory health check
2. secret scan (scan-only by default)
3. drift detection
4. compile memory pack (unless skipped)

This is a wrapper around the standalone Mneme tools.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

TOOLS = {
    'check': ROOT / 'mneme_memory_check.py',
    'compile': ROOT / 'mneme_compile_memory.py',
    'scrub': ROOT / 'mneme_secret_scrub.py',
    'drift': ROOT / 'mneme_memory_drift.py',
}


def run_json(cmd: list[str]) -> dict:
    cp = subprocess.run(cmd, capture_output=True, text=True)
    if cp.returncode not in (0, 1):
        raise RuntimeError(f"Command failed ({cp.returncode}): {' '.join(cmd)}\n{cp.stderr or cp.stdout}")
    return json.loads(cp.stdout)


def main() -> int:
    ap = argparse.ArgumentParser(description='Run the Mneme maintenance flow.')
    ap.add_argument('--root', default='.', help='Workspace root')
    ap.add_argument('--out', default='compiled', help='Compile output directory')
    ap.add_argument('--apply-scrub', action='store_true', help='Rewrite files when scrubber finds secrets')
    ap.add_argument('--skip-check', action='store_true')
    ap.add_argument('--skip-scrub', action='store_true')
    ap.add_argument('--skip-drift', action='store_true')
    ap.add_argument('--skip-compile', action='store_true')
    ap.add_argument('--json', action='store_true', help='Emit JSON summary')
    args = ap.parse_args()

    root = str(Path(args.root).expanduser().resolve())
    out = str(Path(args.out).expanduser().resolve())
    summary: dict[str, object] = {
        'root': root,
        'steps': {},
    }

    exit_code = 0

    if not args.skip_check:
        data = run_json([str(TOOLS['check']), '--json'])
        summary['steps']['check'] = data
        if not data.get('ok', False):
            exit_code = max(exit_code, 1)

    if not args.skip_scrub:
        cmd = [str(TOOLS['scrub']), '--root', root, '--json']
        if args.apply_scrub:
            cmd.insert(-1, '--apply')
        data = run_json(cmd)
        summary['steps']['scrub'] = data
        if data.get('total_findings', 0):
            exit_code = max(exit_code, 1)

    if not args.skip_drift:
        data = run_json([str(TOOLS['drift']), '--root', root, '--json'])
        summary['steps']['drift'] = data
        counts = data.get('counts', {})
        if counts.get('contradictions', 0) or counts.get('stale', 0):
            exit_code = max(exit_code, 1)

    if not args.skip_compile:
        cp = subprocess.run([str(TOOLS['compile']), '--root', root, '--out', out], capture_output=True, text=True)
        if cp.returncode != 0:
            raise RuntimeError(cp.stderr or cp.stdout)
        summary['steps']['compile'] = {
            'ok': True,
            'out': out,
            'message': cp.stdout.strip(),
        }

    if args.json:
        print(json.dumps(summary, indent=2))
        return exit_code

    print('Mneme run')
    print('=========')
    print(f'root: {root}')
    if 'check' in summary['steps']:
        d = summary['steps']['check']
        print(f"check: {'ok' if d.get('ok') else 'needs attention'} ({d.get('summary', {}).get('checks', '?')} checks)")
    if 'scrub' in summary['steps']:
        d = summary['steps']['scrub']
        print(f"scrub: {d.get('total_findings', 0)} findings")
    if 'drift' in summary['steps']:
        d = summary['steps']['drift']
        c = d.get('counts', {})
        print(f"drift: {c.get('contradictions', 0)} contradictions, {c.get('stale', 0)} stale")
    if 'compile' in summary['steps']:
        print(f"compile: {summary['steps']['compile']['out']}")
    return exit_code


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except RuntimeError as e:
        print(f'ERROR: {e}', file=sys.stderr)
        raise SystemExit(2)
