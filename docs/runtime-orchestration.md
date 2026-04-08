# Mneme Runtime Orchestration

Mneme now has a runtime-side bridge script.

It does not directly spawn agents by itself from inside the repo.
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

## Privacy defaults

Runtime prep is now stricter by default:
- runtime artifacts default under workspace-local `.mneme-runtime/`
- `prepare-task` requires explicit `--allow-agent-export`
- that makes the off-box boundary deliberate instead of casual

## Commands

### 1. Prepare a runtime task

```bash
./scripts/mneme_runtime_orchestrate.py prepare-task \
  --root /path/to/workspace \
  --category projects \
  --allow-agent-export
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
  --raw-out /path/to/workspace/.mneme-runtime/raw \
  --candidate ./candidate-projects.json \
  --materialize-out /path/to/workspace/.mneme-runtime/materialized-projects
```

This does:
- validate evidence refs
- materialize category output
- optional merge into a reviewed pack

## Honest boundary

This is still the real split:
- **repo script** prepares and applies
- **OpenClaw runtime** dispatches and receives

That keeps the repo honest and the runtime first-class.
