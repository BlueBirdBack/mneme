# Mneme Candidate Materialization

After an LLM produces candidate compiled entries and Mneme validates them, a deterministic step still needs to:
- assign final ids
- assign document ids
- write structured compiled outputs
- render readable markdown views

## Script

- `scripts/mneme_materialize_candidates.py`

## Usage

```bash
./scripts/mneme_materialize_candidates.py \
  --category projects \
  --input ./candidate-projects.json \
  --out /tmp/mneme-materialized-projects
```

## What it writes

- `documents.jsonl`
- `entries.jsonl`
- `<category>.md`

## Why this exists

This keeps the LLM focused on judgment and grouping.
Mneme still owns final structure, ids, and output layout.
