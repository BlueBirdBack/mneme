# Mneme Continuation Guide

If you are resuming Mneme work in a new session, start here.

## Current status

Mneme now has:
- memory health check
- secret scrubber
- drift detector
- raw evidence ingest
- structured compiler outputs
- LLM-assisted compile scaffold
- candidate validation + materialization
- reviewed-pack merge
- runtime orchestration bridge
- a proven automatic runtime dispatch loop

The first serious reviewed pack has already been proven across:
- `projects`
- `systems`
- `decisions`
- `incidents`

## Stable assumptions

Repo:
- `/path/to/mneme`

Workspace root:
- `/path/to/workspace`

Do **not** depend on old temporary output directories still existing on the next day. Regenerate fresh outputs.

## How to continue

### 1. Verify the Mneme baseline

```bash
cd /path/to/mneme
./scripts/mneme_run.py --root /path/to/workspace --skip-scrub --json
```

Expected baseline:
- memory check ok
- drift = 0 contradictions / 0 stale

### 2. Prepare a fresh runtime task

```bash
./scripts/mneme_runtime_orchestrate.py prepare-task \
  --root /path/to/workspace \
  --category projects \
  --max-items 25 \
  --raw-out /path/to/output/raw \
  --bundles-out /path/to/output/bundles \
  --materialize-out /path/to/output/materialized-projects
```

### 3. Dispatch through the runtime
Use the produced `taskPrompt` with an OpenClaw agent/sub-agent.

### 4. Apply the result

```bash
./scripts/mneme_runtime_orchestrate.py apply-result \
  --category projects \
  --raw-out /path/to/output/raw \
  --candidate /path/to/candidate-projects.json \
  --materialize-out /path/to/output/materialized-projects
```

### 5. Merge reviewed categories when ready

```bash
./scripts/mneme_merge_pack.py \
  --inputs /path/to/output/materialized-projects /path/to/output/materialized-systems \
           /path/to/output/materialized-decisions /path/to/output/materialized-incidents \
  --out /path/to/output/reviewed-pack
```

## Highest-value next work

1. **Multi-category automatic run**
   - one runtime job that iterates categories and merges at the end

2. **Result normalization**
   - reduce manual cleanup when agent output uses slightly different field names/shapes

3. **Review summaries**
   - generate a compact summary of what changed in the reviewed pack

4. **Better merge quality**
   - dedupe overlapping entries across categories where useful

## Important lesson

Pure scripts were good for plumbing and hygiene.
Useful memory compilation required an agent/LLM judgment layer.
The winning architecture is:

**deterministic pipeline + agent judgment + deterministic validation/materialization**
