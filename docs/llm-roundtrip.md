# Mneme LLM Roundtrip

Mneme now has a wrapper for the first real AI-assisted compile loop.

## Script

- `scripts/mneme_llm_roundtrip.py`

## What it does

Runs this flow:
1. ingest raw evidence
2. prepare LLM bundles
3. optionally validate a candidate JSON file
4. optionally materialize validated entries into compiled outputs

## Usage

Prepare bundles for one category:

```bash
./scripts/mneme_llm_roundtrip.py \
  --root /path/to/workspace \
  --category projects \
  --json
```

Run the full loop with a candidate file:

```bash
./scripts/mneme_llm_roundtrip.py \
  --root /path/to/workspace \
  --category projects \
  --candidate ./candidate-projects.json \
  --json
```

## Why this matters

This is the seam where Mneme stops being only deterministic plumbing and starts supporting real judgment:
- deterministic ingest/prep/validation/materialization
- LLM grouping/summarization in the middle

That is the intended architecture.
