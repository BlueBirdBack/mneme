# Mneme Ingest Pipeline (v1)

Issue #2 starts simple on purpose.

Mneme does not need ten data sources before it becomes useful.
It needs one reliable ingest path that turns OpenClaw memory files into raw evidence.

## Script

- `scripts/mneme_ingest_memory.py`

## Scope for v1

Input:
- `MEMORY.md`
- `memory/*.md`

Output:
- `raw/sources.jsonl`
- `raw/items.jsonl`
- `raw/report.json`

## What it does

- creates one `EvidenceSource` per source file
- creates `EvidenceItem` records from:
  - headings
  - bullets
  - section blocks
- preserves provenance
- redacts obvious secrets in item text
- writes deterministic JSONL output

## What it does not do yet

- session transcript ingest
- repo file ingest
- PDFs / web pages / images
- entity linking
- contradiction resolution
- promotion into compiled memory

## Usage

```bash
./scripts/mneme_ingest_memory.py \
  --root ~/.openclaw/workspace \
  --out /tmp/mneme-raw
```

## Why JSONL

JSONL is enough for v1 because it is:
- append-friendly
- diffable
- inspectable
- easy to rebuild and pipe into later stages

## Relationship to the evidence model

This ingest pipeline is valid because it emits the fields defined in:
- `docs/evidence-model.md`

That is the contract.
