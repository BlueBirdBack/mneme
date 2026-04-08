# Mneme Memory Drift

Mneme's next job after recall repair and secret scrubbing is to catch **memory drift**.

That now means three things:
- likely contradictions
- likely duplicates
- likely stale facts

## Script

- `scripts/mneme_memory_drift.py`

## What it does

- scans `MEMORY.md` and `memory/*.md`
- extracts a few high-value fact types (provider, model, key ports, protocol versions, checkout paths)
- flags keys that have multiple distinct values across memory
- clusters likely duplicate facts that appear in multiple files
- flags old note lines that still look time-sensitive (`current state`, `pending`, `not yet`, `TODO`, etc.)
- adds simple **severity** and **confidence** scoring to help triage

## Usage

```bash
./scripts/mneme_memory_drift.py --root ~/.openclaw/workspace
./scripts/mneme_memory_drift.py --root ~/.openclaw/workspace --stale-days 14
./scripts/mneme_memory_drift.py --root ~/.openclaw/workspace --json
```

## Important limitation

This is a **review tool**, not a truth oracle.

A contradiction candidate means:
- two different values were found
- a human or later Mneme pass should decide which one is current

A duplicate candidate means:
- the same normalized fact seems to appear in multiple files
- it may deserve merge, promotion, or suppression

A stale candidate means:
- an old note still reads like live truth
- it may need trimming, promotion, or explicit supersession
