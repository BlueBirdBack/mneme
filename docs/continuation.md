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

## Stable paths

Repo:
- `/home/openclaw/.openclaw/workspace/mneme`

Workspace root:
- `/home/openclaw/.openclaw/workspace`

Do **not** depend on old `/tmp` paths being present tomorrow. Regenerate fresh outputs.

## How to continue tomorrow

### 1. Verify Mneme baseline

```bash
cd /home/openclaw/.openclaw/workspace/mneme
./scripts/mneme_run.py --root /home/openclaw/.openclaw/workspace --skip-scrub --json
```

Expected baseline:
- memory check ok
- drift = 0 contradictions / 0 stale

### 2. Prepare a fresh runtime task

```bash
./scripts/mneme_runtime_orchestrate.py prepare-task \
  --root /home/openclaw/.openclaw/workspace \
  --category projects \
  --max-items 25 \
  --raw-out /tmp/mneme-next-raw \
  --bundles-out /tmp/mneme-next-bundles \
  --materialize-out /tmp/mneme-next-materialized-projects
```

### 3. Dispatch through the runtime
Use the produced `taskPrompt` with an OpenClaw agent/sub-agent.

### 4. Apply the result

```bash
./scripts/mneme_runtime_orchestrate.py apply-result \
  --category projects \
  --raw-out /tmp/mneme-next-raw \
  --candidate /path/to/candidate-projects.json \
  --materialize-out /tmp/mneme-next-materialized-projects
```

### 5. Merge reviewed categories when ready

```bash
./scripts/mneme_merge_pack.py \
  --inputs /tmp/mneme-next-materialized-projects /tmp/mneme-next-materialized-systems \
           /tmp/mneme-next-materialized-decisions /tmp/mneme-next-materialized-incidents \
  --out /tmp/mneme-next-reviewed-pack
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
