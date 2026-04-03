# Mneme Compiler

Mneme's second job is to turn scattered memory notes into a usable pack.

Not by publishing someone's private memory.
Not by pretending summaries are truth.
By compiling notes into reviewable artifacts with provenance.

## Goal

Take this:
- `MEMORY.md`
- `memory/*.md`

And produce this:
- `compiled/documents.jsonl`
- `compiled/entries.jsonl`
- `compiled/projects.md`
- `compiled/systems.md`
- `compiled/decisions.md`
- `compiled/incidents.md`
- `compiled/timeline.md`
- `compiled/report.md`

## Rules

- keep provenance
- redact obvious secrets in generated text
- treat output as candidate memory, not final truth
- prefer concise durable facts over session sludge
- do not commit private compiled memory packs to the public repo by default

## First implementation

Script:
- `scripts/mneme_compile_memory.py`

What it does in the first pass:
- reads Mneme raw evidence (`raw/sources.jsonl`, `raw/items.jsonl`) when available
- falls back to direct markdown parsing only as a legacy path
- extracts candidate lines by simple deterministic rules
- filters heading-only entries out of compiled memory
- suppresses low-value project noise such as TODOs, branch names, and commit-hash litter
- groups lines into project/system/decision/incident buckets
- deduplicates timeline events more aggressively
- builds a timeline from evidence/source metadata
- writes structured compiled JSONL
- renders markdown views from the compiled layer
- writes a report with source counts

What it does **not** do yet:
- contradiction resolution
- staleness scoring
- entity linking
- promotion back into `MEMORY.md`
- LLM synthesis

## Usage

```bash
./scripts/mneme_compile_memory.py --root /path/to/workspace --raw /path/to/raw --out /path/to/compiled
```

Example for a local OpenClaw workspace:

```bash
./scripts/mneme_compile_memory.py --root ~/.openclaw/workspace --raw ./raw --out ./compiled
```

## Why this matters

Raw memory files are chronological.
Useful memory is structural.

The compiler is the bridge between the two.
