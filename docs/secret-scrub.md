# Mneme Secret Scrub

Historical memory files have a bad habit: they keep raw secrets long after the work is done.

Mneme's secret scrubber exists to catch that.

## Script

- `scripts/mneme_secret_scrub.py`

## What it does

- scans `MEMORY.md`, `USER.md`, `IDENTITY.md`, and `memory/*.md`
- finds likely raw tokens, API keys, bearer strings, and password fields
- prints findings in **redacted form**
- ranks findings by **severity** and **confidence** so obvious secrets surface first
- can optionally rewrite files in place and create `.bak` backups

## Usage

```bash
./scripts/mneme_secret_scrub.py --root ~/.openclaw/workspace
./scripts/mneme_secret_scrub.py --root ~/.openclaw/workspace --json
./scripts/mneme_secret_scrub.py --root ~/.openclaw/workspace --apply
./scripts/mneme_secret_scrub.py --root ~/.openclaw/workspace --apply --apply-generic-fields
```

## Output shape

Review output is now grouped into:
- highest priority
- needs review
- likely false positives / low-confidence
- files worth checking first

This keeps real credential-bearing lines from getting buried under noisy generic matches.

## Apply mode

Default `--apply` is conservative:
- strong secret patterns are rewritten automatically
- generic token/password fields are **not** rewritten unless you pass `--apply-generic-fields`
- `.bak` backups are created before rewrite

## Why this matters

A memory system should help recall work, not leak credentials from old notes.
