# Milestone 1 Checklist — Recall Works

Goal: make Six's memory recall healthy, testable, and boringly reliable.

## Live repair
- [x] Inspect current memory configuration
- [x] Identify real failure mode
- [x] Switch memory search off broken `local` embeddings
- [x] Set provider to `gemini`
- [x] Verify gateway restart completed cleanly
- [x] Verify memory status succeeds
- [x] Verify index exists and is current
- [x] Verify semantic recall returns useful results
- [x] Verify citations/source paths are available when needed

## Mneme checks to build
- [x] Detect broken provider configuration
- [x] Detect missing embedding dependencies
- [x] Detect stale or missing memory indexes
- [x] Run a basic recall test suite against live memory
- [x] Report clear failure reasons and suggested fixes

## Exit criteria
- [x] `openclaw memory status --deep` succeeds
- [x] at least one semantic recall query returns relevant memory
- [x] recall is no longer dependent on unavailable local embeddings
- [x] the failure is documented as Mneme's first real-world target
