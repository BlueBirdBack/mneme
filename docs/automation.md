# Mneme Automation

Mneme is meant to become routine maintenance, not a one-off rescue project.

## Current live automation

A daily OpenClaw cron is configured locally for Six.

### Schedule
- **9:15 AM**
- **Timezone:** `Asia/Shanghai`

### Purpose
Run the Mneme maintenance flow and stay quiet unless something needs attention.

### Current behavior
The daily run uses the stable local repo path:

```bash
/home/openclaw/.openclaw/workspace/mneme/scripts/mneme_run.py \
  --root /home/openclaw/.openclaw/workspace \
  --out /tmp/mneme-cron-pack \
  --skip-scrub \
  --json
```

Interpretation rule:
- if memory check is healthy and drift is clean, say nothing
- if recall breaks, contradictions appear, or stale items appear, report only the deltas/problems

## Why `--skip-scrub` is used right now
The scrubber is useful, but daily automatic rewrite is too aggressive until false positives are tightened further.

So the current daily automation is:
- check
- drift
- compile
- no automatic scrub rewrite

## Local state vs repo state
The cron job itself lives in the local OpenClaw scheduler, not in git.

The repo documents:
- intended automation behavior
- runner usage
- expected schedule pattern

The local runtime holds:
- actual cron registration
- delivery target
- session binding

## Recommended next step
Once scrub false positives are tighter, extend daily automation to include scan-only scrub reporting, then later optional auto-scrub for clearly safe patterns.
