# Mneme Retrieval

Mneme now has a lexical-first retrieval helper with citations.

## Script

- `scripts/mneme_retrieve.py`

## What it does

Baseline evidence mode:
- searches raw evidence in `raw/items.jsonl`
- ranks results by simple lexical overlap
- supports basic scoping by kind, path, heading, and time
- returns inspectable citations for every hit

Activity mode:
- detects recent-activity style queries like "what did you do in the last 24 hours"
- can infer simple time windows from phrases like `last 24 hours`, `today`, and `yesterday`
- supplements raw evidence with:
  - recent git commits discovered under the workspace root
  - recent OpenClaw session activity from `~/.openclaw/agents`
- ranks recent direct evidence above older durable-memory hits for activity queries

## Usage

```bash
./scripts/mneme_retrieve.py --root ~/.openclaw/workspace --query "bdeep map truth layer"
./scripts/mneme_retrieve.py --root ~/.openclaw/workspace --query "Bruce Bell timezone" --heading user
./scripts/mneme_retrieve.py --root ~/.openclaw/workspace --query "Anima Protocol" --since 2026-04-01T00:00:00Z --json

# Auto activity mode from the query
./scripts/mneme_retrieve.py --root ~/.openclaw/workspace --query "what did you do in the last 24 hours" --json

# Force activity mode explicitly
./scripts/mneme_retrieve.py --root ~/.openclaw/workspace --mode activity --query "what changed yesterday"
```

## Modes

- `--mode auto` (default)
  - uses activity mode when the query looks like recent-work / timeline recall
  - otherwise uses baseline evidence mode
- `--mode evidence`
  - only searches raw Mneme evidence
- `--mode activity`
  - searches raw evidence plus recent git/session activity

## Current boundary

This is still a **lexical-first** retriever.
It is better at recent-activity reconstruction now, but it is not a full semantic planner or a complete session-ingest pipeline yet.

That means the improvement is practical, not magical:
- recent git/session evidence can now be surfaced directly
- durable raw evidence still works as before
- deeper semantic ranking can still be layered on later without changing the citation-friendly result shape
