# Mneme Memory Drift

Mneme's next job after recall repair and secret scrubbing is to catch **memory drift**.

That means two things:
- likely contradictions
- likely stale facts

## Script

- `scripts/mneme_memory_drift.py`

## What it does

- scans `MEMORY.md` and `memory/*.md`
- extracts a few high-value fact types (provider, model, key ports, protocol versions, checkout paths)
- flags keys that have multiple distinct values across memory
- flags old note lines that still look time-sensitive (`current state`, `pending`, `not yet`, `fixing`, `TODO`, etc.)

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

A stale candidate means:
- an old note still reads like live truth
- it may need trimming, promotion, or explicit supersession
