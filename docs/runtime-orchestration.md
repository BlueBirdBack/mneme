# Mneme Runtime Orchestration

Mneme now has a runtime-side bridge script.

It does not directly spawn agents by itself.
Instead, it prepares a ready-to-send agent task and then applies the returned result.

## Script

- `scripts/mneme_runtime_orchestrate.py`

## Why this exists

The repo already had the deterministic pieces:
- ingest
- prepare bundles
- validate
- materialize
- merge

What was missing was the runtime seam between:
- repo scripts
- OpenClaw agent dispatch

This script is that seam.

## Commands

### 1. Prepare a runtime task

```bash
./scripts/mneme_runtime_orchestrate.py prepare-task \
  --root ~/.openclaw/workspace \
  --category projects
```

This outputs JSON containing:
- chosen bundle path
- raw/bundle/materialize paths
- a fully assembled `taskPrompt`
- summary of the underlying roundtrip prep

The OpenClaw runtime can take `taskPrompt` and send it to an agent.

### 2. Apply an agent result

```bash
./scripts/mneme_runtime_orchestrate.py apply-result \
  --category projects \
  --raw-out /tmp/mneme-runtime-raw \
  --candidate ./candidate-projects.json \
  --materialize-out /tmp/mneme-runtime-materialized-projects
```

This does:
- validate evidence refs
- materialize category output
- optional merge into a reviewed pack

## Intended runtime flow

1. `prepare-task`
2. runtime sends `taskPrompt` to an agent
3. agent returns JSON
4. write that JSON to a candidate file
5. `apply-result`
6. optional merge pack

## Honest boundary

This is the real boundary:
- **repo script** prepares and applies
- **OpenClaw runtime** dispatches and receives

That keeps the repo honest and the runtime first-class.
