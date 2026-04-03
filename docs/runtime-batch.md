# Mneme Runtime Batch Flow

Mneme can now prepare and apply **multi-category** runtime runs.

This sits above the single-category runtime bridge.

## Script

- `scripts/mneme_runtime_batch.py`

## Purpose

Batch together the four core categories:
- `projects`
- `systems`
- `decisions`
- `incidents`

so the runtime can iterate category tasks and then merge one reviewed pack.

## Commands

### 1. Prepare batch tasks

```bash
./scripts/mneme_runtime_batch.py prepare-batch \
  --root /path/to/workspace \
  --out /path/to/output/batch
```

This writes:
- `manifest.json`
- `task-projects.json`
- `task-systems.json`
- `task-decisions.json`
- `task-incidents.json`

Each task file contains a runtime-ready `taskPrompt`.

### 2. Apply returned candidates

```bash
./scripts/mneme_runtime_batch.py apply-batch \
  --manifest /path/to/output/batch/manifest.json \
  --candidate-map \
    projects=/path/to/candidate-projects.json \
    systems=/path/to/candidate-systems.json \
    decisions=/path/to/candidate-decisions.json \
    incidents=/path/to/candidate-incidents.json \
  --reviewed-out /path/to/output/reviewed-pack
```

This does:
- validate each category result
- materialize each category output
- merge all successful categories into one reviewed pack

## Why this matters

Single-category automatic dispatch was already proven.
This batch layer is the next step toward a full Mneme compile job that builds a serious reviewed pack in one runtime-guided flow.
