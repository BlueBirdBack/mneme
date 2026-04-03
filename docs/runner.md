# Mneme Runner

Mneme now has a single wrapper script for routine maintenance.

## Script

- `scripts/mneme_run.py`

## What it does

Runs the Mneme flow in one shot:
1. memory health check
2. secret scan (or scrub if `--apply-scrub` is used)
3. drift detection
4. ingest raw evidence
5. compile from raw evidence

## Usage

```bash
./scripts/mneme_run.py --root ~/.openclaw/workspace --out /tmp/mneme-pack
./scripts/mneme_run.py --root ~/.openclaw/workspace --skip-compile
./scripts/mneme_run.py --root ~/.openclaw/workspace --apply-scrub --json
```

## Notes

- default scrub mode is scan-only
- compile output should usually stay out of git
- non-zero exit means Mneme found something that needs attention
