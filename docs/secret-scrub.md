# Mneme Secret Scrub

Historical memory files have a bad habit: they keep raw secrets long after the work is done.

Mneme's secret scrubber exists to catch that.

## Script

- `scripts/mneme_secret_scrub.py`

## What it does

- scans `MEMORY.md`, `USER.md`, `IDENTITY.md`, and `memory/*.md`
- finds likely raw tokens, API keys, bearer strings, and password fields
- prints findings in **redacted form**
- can optionally rewrite files in place and create `.bak` backups

## Usage

```bash
./scripts/mneme_secret_scrub.py --root ~/.openclaw/workspace
./scripts/mneme_secret_scrub.py --root ~/.openclaw/workspace --json
./scripts/mneme_secret_scrub.py --root ~/.openclaw/workspace --apply
```

## Rules

- redact obvious raw secrets
- keep useful access facts in summarized form when possible
- create backups before rewrite
- review findings instead of blindly trusting pattern matching

## Why this matters

A memory system should help recall work, not leak credentials from old notes.
