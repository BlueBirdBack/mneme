# Mneme Automation

Mneme is meant to become routine maintenance, not a one-off rescue project.

## Current automation pattern

A local scheduler can run Mneme on a daily cadence.

### Example schedule
- once per day
- in the user's local timezone

### Purpose
Run the Mneme maintenance flow and stay quiet unless something needs attention.

### Example behavior
A typical run can use the stable local repo path and the Mneme runner:

```bash
/path/to/mneme/scripts/mneme_run.py \
  --root /path/to/workspace \
  --out /path/to/output/compiled \
  --skip-scrub \
  --json
```

Interpretation rule:
- if memory check is healthy and drift is clean, say nothing
- if recall breaks, contradictions appear, or stale items appear, report only the deltas/problems

## Why `--skip-scrub` is used by default
The scrubber is useful, but daily automatic rewrite is too aggressive until false positives are tightened further.

So a conservative daily automation pattern is:
- check
- drift
- ingest
- compile
- no automatic scrub rewrite

## Local state vs repo state
The scheduler job itself lives in the local runtime, not in git.

The repo documents:
- intended automation behavior
- runner usage
- expected schedule pattern

The local runtime holds:
- actual job registration
- delivery target
- session binding

## Recommended next step
Once scrub false positives are tighter, extend daily automation to include scan-only scrub reporting, then later optional auto-scrub for clearly safe patterns.
