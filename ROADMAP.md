# Mneme Roadmap

## Phase 0 — Project spine
- Define project language and core promises
- Establish v1 scope: personal memory first
- Create initial repo docs, architecture notes, and tracked issues

## Phase 1 — Raw evidence ingestion
Goal: collect the things an agent actually did and saw.

Deliverables:
- session/chat ingest
- markdown/doc ingest
- repo/file ingest
- normalized evidence model
- source identity and timestamps

Success criteria:
- raw evidence can be captured without losing provenance
- every evidence item has enough metadata to trace it back to origin

## Phase 2 — Memory compilation
Goal: turn evidence into structured, usable memory.

Deliverables:
- entity extraction (people, projects, systems, repos, tasks)
- decision/timeline extraction
- memory compiler output format
- source-linked notes and summaries
- confidence/state markers (observed, inferred, stale, contradicted)

Success criteria:
- memory artifacts are more useful than raw logs
- important claims can be traced back to source evidence

## Phase 3 — Retrieval and recall
Goal: let agents recover what matters when they need it.

Deliverables:
- semantic + lexical retrieval
- recall API/tooling
- answer assembly with citations
- scoped recall by person/project/topic/time

Success criteria:
- agents can answer prior-context questions with evidence
- recall quality beats ad-hoc note grep and fragile session memory

## Phase 4 — Memory hygiene
Goal: keep memory from rotting.

Deliverables:
- duplicate detection
- contradiction detection
- stale fact surfacing
- repair/review workflows
- provenance-aware diffing of memory artifacts

Success criteria:
- memory quality improves over time instead of degrading

## Phase 5 — Promotion to shared memory
Goal: safely move verified knowledge from local memory into shared memory.

Deliverables:
- promotion rules
- review/audit trail
- shared namespace model
- ownership and conflict-resolution rules

Success criteria:
- shared memory is useful without becoming a rumor mill

## Candidate first issues
1. Define the evidence model
2. Build the first ingest pipeline
3. Design the memory compiler output format
4. Implement retrieval with citations
5. Add contradiction/staleness detection
6. Define promotion rules for shared memory
