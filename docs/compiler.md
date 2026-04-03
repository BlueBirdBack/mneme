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
- reads OpenClaw-style memory sources
- extracts candidate lines by simple deterministic rules
- groups them into project/system/decision/incident buckets
- builds a timeline from dated note headings
- writes a report with source counts

What it does **not** do yet:
- contradiction resolution
- staleness scoring
- entity linking
- promotion back into `MEMORY.md`
- LLM synthesis

## Usage

```bash
./scripts/mneme_compile_memory.py --root /path/to/workspace --out /path/to/compiled
```

Example for a local OpenClaw workspace:

```bash
./scripts/mneme_compile_memory.py --root ~/.openclaw/workspace --out ./compiled
```

## Why this matters

Raw memory files are chronological.
Useful memory is structural.

The compiler is the bridge between the two.
