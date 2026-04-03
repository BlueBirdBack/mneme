# Build Memory with Agents

This is the first practical Mneme playbook for building a reviewed memory pack with agent help.

## Goal

Turn raw OpenClaw memory into a reviewed compiled pack through a repeatable flow:

1. ingest raw evidence
2. prepare category bundles
3. send a bundle to an agent
4. receive candidate JSON
5. validate the evidence refs
6. materialize category outputs
7. merge category outputs into one reviewed pack

## Deterministic pieces

Mneme already provides the deterministic shell:
- `scripts/mneme_ingest_memory.py`
- `scripts/mneme_llm_compile.py`
- `scripts/mneme_materialize_candidates.py`
- `scripts/mneme_llm_roundtrip.py`
- `scripts/mneme_merge_pack.py`

## Current runtime boundary

The one thing the repo does **not** own by itself is the live agent dispatch step.
That still depends on the OpenClaw runtime/tool layer.

So the current architecture is:
- repo scripts = ingest, prep, validate, materialize, merge
- runtime tools = send bundle to agent, receive JSON back

That is deliberate. It avoids pretending a standalone shell script can summon agents without the runtime.

## Category-by-category flow

### 1. Prepare bundles

```bash
./scripts/mneme_llm_roundtrip.py \
  --root ~/.openclaw/workspace \
  --category projects \
  --json
```

### 2. Agent pass
Use the prepared bundle as input to an agent and ask for candidate JSON only.

### 3. Validate + materialize

```bash
./scripts/mneme_llm_compile.py validate \
  --raw /tmp/mneme-llm-raw \
  --input ./candidate-projects.json

./scripts/mneme_materialize_candidates.py \
  --category projects \
  --input ./candidate-projects.json \
  --out /tmp/mneme-materialized-projects
```

### 4. Merge reviewed categories

```bash
./scripts/mneme_merge_pack.py \
  --inputs /tmp/mneme-materialized-projects /tmp/mneme-materialized-systems \
           /tmp/mneme-materialized-decisions /tmp/mneme-materialized-incidents \
  --out /tmp/mneme-reviewed-pack
```

## Proven categories so far

The agent-connected loop has already been proven for:
- `projects`
- `systems`
- `decisions`
- `incidents`

That is the first serious Mneme memory pack.

## What remains

To make this a one-command runtime flow, the next step is an OpenClaw-side wrapper that can:
- choose a category bundle
- dispatch it to an agent automatically
- capture the JSON output
- call validate/materialize automatically
- optionally merge the reviewed pack

That wrapper belongs at the runtime/tool layer, not in a fake standalone repo script.
