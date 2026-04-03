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
- `scripts/mneme_runtime_orchestrate.py`

## Current architecture

The architecture is now split cleanly like this:
- repo scripts = ingest, prep, validate, materialize, merge, runtime bridge
- runtime tools = send bundle to agent, receive JSON back

That is deliberate. It avoids pretending a standalone repo script can summon agents without the runtime.

## Category-by-category flow

### 1. Prepare bundles

```bash
./scripts/mneme_llm_roundtrip.py \
  --root /path/to/workspace \
  --category projects \
  --json
```

### 2. Agent pass
Use the prepared bundle as input to an agent and ask for candidate JSON only.

### 3. Validate + materialize

```bash
./scripts/mneme_llm_compile.py validate \
  --raw /path/to/output/raw \
  --input ./candidate-projects.json

./scripts/mneme_materialize_candidates.py \
  --category projects \
  --input ./candidate-projects.json \
  --out /path/to/output/materialized-projects
```

### 4. Merge reviewed categories

```bash
./scripts/mneme_merge_pack.py \
  --inputs /path/to/output/materialized-projects /path/to/output/materialized-systems \
           /path/to/output/materialized-decisions /path/to/output/materialized-incidents \
  --out /path/to/output/reviewed-pack
```

## Proven categories so far

The agent-connected loop has already been proven for:
- `projects`
- `systems`
- `decisions`
- `incidents`

That is the first serious Mneme memory pack.

## Proven runtime result

The runtime bridge is also proven now:
- prepare-task generated a real category task
- the runtime dispatched it to an agent automatically
- the agent returned candidate JSON
- apply-result validated and materialized it
- the reviewed pack merged successfully

So Mneme has now proven both:
- category-by-category agent compilation
- automatic runtime dispatch through the bridge layer

## What remains

The next work is not basic capability. It is refinement:
- multi-category automatic runs
- result normalization to reduce manual cleanup
- better merge quality and review summaries
- a first-class runtime command for full Mneme compile jobs
