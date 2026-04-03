# Mneme LLM-Assisted Compiler

Mneme's deterministic layer is good at:
- ingest
- provenance
- redaction
- validation
- rendering

It is not good enough at:
- grouping related evidence into one strong entry
- deciding what is durable vs noise
- summarizing without flattening important nuance
- deduping near-identical notes with different wording

That is where the LLM belongs.

## Architecture

Use an LLM as a **judgment layer**, not as the entire memory system.

### Deterministic layers
- ingest raw evidence
- preserve provenance
- prepare evidence bundles
- validate LLM output shape and refs
- assign final ids / render output

### LLM layer
- group related evidence
- produce candidate compiled entries
- summarize and tag
- mark state (`observed`, `historical`, `stale`, etc.)

## Script

- `scripts/mneme_llm_compile.py`

## Modes

### 1. Prepare bundles
Creates stable JSON bundles for an agent/LLM to read.

```bash
./scripts/mneme_llm_compile.py prepare \
  --raw /tmp/mneme-raw \
  --out /tmp/mneme-llm-bundles
```

Output:
- `manifest.json`
- `SYSTEM_PROMPT.md`
- `bundle-<category>-NN.json`

### 2. Validate candidate output
Checks that LLM-produced candidate entries:
- have required fields
- use valid states
- reference real evidence ids from raw input

```bash
./scripts/mneme_llm_compile.py validate \
  --raw /tmp/mneme-raw \
  --input ./candidate-projects.json
```

## Candidate output shape

The LLM should output either:
- a JSON list of entries
- or `{ "entries": [...] }`

Each candidate entry should include:
- `title`
- `summary`
- `state`
- `evidenceRefs`
- optional `facts`
- optional `relations`

The deterministic wrapper should assign final ids and document ids later.

## Why this shape

This keeps the boundary clean:
- LLM decides meaning
- Mneme decides structure, provenance, and validity

That is the right split.
