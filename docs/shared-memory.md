# Shared Memory Promotion Rules

Mneme is local-first.
Shared memory should be the promoted subset, not a rumor bucket.

## Promotion rule

A fact should move from local memory to shared memory only if it is:
- durable enough to matter beyond one session
- useful to more than one agent or operator
- backed by inspectable provenance
- reviewed by a human or an approved review workflow

## What qualifies

Good promotion candidates:
- stable infrastructure facts
- canonical project decisions
- shared operational procedures
- verified ownership / routing facts
- incident learnings that remain true after cleanup

Bad promotion candidates:
- raw credentials
- private personal details without clear need
- transient TODOs / blockers / status chatter
- speculative or unresolved claims
- one-off session debris

## Required audit trail

Every promoted item should retain:
- source evidence refs
- who approved promotion
- when it was promoted
- which local item(s) it came from
- current state (`observed`, `inferred`, `historical`, `stale`, `contradicted`)

## Ownership and conflicts

- each shared item needs an owning agent/team/operator
- conflicts should create a review candidate, not silent overwrite
- the newer claim does not automatically win
- contradictory shared facts must stay review-visible until resolved

## Review model

Default review posture:
- local compile can be automatic
- shared promotion must be explicit
- bulk promotion should produce a review bundle first
- secret scrub should run before promotion

## Safe default

If a fact is useful but sensitive, keep it local and promote a sanitized derivative instead.
