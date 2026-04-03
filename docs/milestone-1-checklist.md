# Milestone 1 Checklist — Recall Works

Goal: make Six's memory recall healthy, testable, and boringly reliable.

## Live repair
- [x] Inspect current memory configuration
- [x] Identify real failure mode
- [x] Switch memory search off broken `local` embeddings
- [x] Set provider to `gemini`
- [ ] Verify gateway restart completed cleanly
- [ ] Verify memory status succeeds
- [ ] Verify index exists and is current
- [ ] Verify semantic recall returns useful results
- [ ] Verify citations/source paths are available when needed

## Mneme checks to build
- [ ] Detect broken provider configuration
- [ ] Detect missing embedding dependencies
- [ ] Detect stale or missing memory indexes
- [ ] Run a basic recall test suite against live memory
- [ ] Report clear failure reasons and suggested fixes

## Exit criteria
- [ ] `openclaw memory status --deep` succeeds
- [ ] at least one semantic recall query returns relevant memory
- [ ] recall is no longer dependent on unavailable local embeddings
- [ ] the failure is documented as Mneme's first real-world target
