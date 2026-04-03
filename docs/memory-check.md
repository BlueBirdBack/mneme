# Mneme Memory Check

The first Mneme check is a small CLI that inspects OpenClaw memory health.

Script:
- `scripts/mneme_memory_check.py`

## What it checks

- memory search enabled/disabled state
- configured memory provider
- missing local embedding dependency (`node-llama-cpp`) when `provider=local`
- `openclaw memory status --deep` success/failure
- index freshness (`Dirty`)
- whether the index is populated
- embeddings readiness
- basic live recall queries

## Usage

```bash
./scripts/mneme_memory_check.py
./scripts/mneme_memory_check.py --json
./scripts/mneme_memory_check.py --skip-query-checks
./scripts/mneme_memory_check.py --query "project deploy details" --query "memory provider"
```

## Why it exists

Mneme v1 starts by catching practical memory failures before they become user-visible.

The first real failure it targets is the one Six already hit:
- memory search configured to `local`
- local embeddings unavailable
- semantic recall broken

This script exists to detect that kind of breakage quickly and report a fix in plain language.
