# Mneme Retrieval

Mneme now has a lexical-first retrieval helper with citations.

## Script

- `scripts/mneme_retrieve.py`

## What it does

- searches raw evidence in `raw/items.jsonl`
- ranks results by simple lexical overlap
- supports basic scoping by kind, path, heading, and time
- returns inspectable citations for every hit

## Usage

```bash
./scripts/mneme_retrieve.py --root ~/.openclaw/workspace --query "bdeep map truth layer"
./scripts/mneme_retrieve.py --root ~/.openclaw/workspace --query "Bruce Bell timezone" --heading user
./scripts/mneme_retrieve.py --root ~/.openclaw/workspace --query "Anima Protocol" --since 2026-04-01T00:00:00Z --json
```

## Current boundary

This is a **lexical-first** recall helper.
It is useful for inspectable retrieval today, but it is not the full semantic recall layer yet.

That means issue #4 is mitigated now, not magically finished forever.
The next step is semantic ranking on top of the same citation-friendly output shape.
