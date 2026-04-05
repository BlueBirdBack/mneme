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

You must pass `--allow-agent-export` explicitly because `taskPrompt` may be sent off-box by the runtime.

The OpenClaw runtime can take `taskPrompt` and send it to an agent.

### 2. Apply an agent result

```bash
./scripts/mneme_runtime_orchestrate.py apply-result \
  --category projects \
  --raw-out /path/to/output/raw \
  --candidate ./candidate-projects.json \
  --materialize-out /path/to/output/materialized-projects
```

This does:
- validate evidence refs
- materialize category output
- optional merge into a reviewed pack

## Proven automatic-dispatch result

The runtime seam has now been proven in a real automatic-dispatch flow:

1. `prepare-task` generated a category task prompt
2. the OpenClaw runtime dispatched that prompt to a real agent automatically
3. the agent returned candidate JSON
4. `apply-result` validated and materialized the result
5. the reviewed pack was merged successfully

This means the full runtime loop is now proven:

**bundle -> agent -> validate -> materialize -> merge**

## Honest boundary

This is still the real split:
- **repo script** prepares and applies
- **OpenClaw runtime** dispatches and receives

That keeps the repo honest and the runtime first-class.

## Next step

The next improvement is not proof-of-concept anymore.
It is productization:
- make automatic dispatch reusable for any supported category (`projects`, `systems`, `decisions`, `incidents`, `people`, `timeline`)
- support multi-category runs
- add `todos` only when the compiler/materializer support is real instead of implied
- standardize result normalization so agent output shape stays consistent
