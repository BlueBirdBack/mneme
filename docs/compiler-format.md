# Mneme Compiler Output Format

The evidence model defines the raw layer.
This document defines the **compiled layer**.

If the evidence model answers:

> What raw thing do we know?

Then the compiler output format answers:

> What durable memory object should an agent actually read?

## Goal

Turn chronological evidence into structured memory artifacts that are:
- readable by agents and humans
- source-backed
- maintainable over time
- explicit about confidence and state

## Design rules

- **Compiled memory is derived from evidence.**
- **Every important compiled claim must point back to evidence.**
- **Compiled memory may summarize, but must not hide provenance.**
- **Compiled memory can express uncertainty, staleness, and contradiction.**
- **The compiler should produce stable shapes, not ad-hoc markdown vibes.**

---

## Two-level compiled model

Mneme v1 uses two compiled objects:

1. **CompiledDocument** — one output artifact such as `projects`, `systems`, `decisions`
2. **CompiledEntry** — one structured memory entry inside that document

Examples:
- `compiled/projects.md` contains many project entries
- `compiled/decisions.md` contains many decision entries
- `compiled/incidents.md` contains many incident entries

---

## CompiledDocument

Represents one compiled memory artifact.

### Required fields

| Field | Type | Meaning |
|---|---|---|
| `id` | string | Stable document identifier |
| `kind` | enum | Document type |
| `title` | string | Human-readable title |
| `generatedAt` | ISO timestamp | When compiler generated it |
| `entryIds` | string[] | Ordered ids of entries inside it |
|
### Optional fields

| Field | Type | Meaning |
|---|---|---|
| `sourceIds` | string[] | Evidence sources used to build the document |
| `meta` | object | Extra generation metadata |
|
### `kind` values for v1

Currently implemented:
- `projects`
- `systems`
- `decisions`
- `incidents`
- `timeline`
- `people`
- `report`

Planned, not implemented yet:
- `todos`

---

## CompiledEntry

Represents one durable structured memory unit.

Examples:
- one project summary
- one system/service summary
- one architecture decision
- one incident summary
- one timeline event

### Required fields

| Field | Type | Meaning |
|---|---|---|
| `id` | string | Stable entry identifier |
| `documentId` | string | Parent `CompiledDocument.id` |
| `entryType` | enum | Specific compiled entry type |
| `title` | string | Entry title |
| `summary` | string | Short compiled description |
| `state` | enum | Current memory state |
| `evidenceRefs` | object[] | References to supporting evidence |
| `updatedAt` | ISO timestamp | Last compiler update time |
|
### Optional fields

| Field | Type | Meaning |
|---|---|---|
| `observedAt` | ISO timestamp | Earliest known observation time |
| `lastConfirmedAt` | ISO timestamp | Latest supporting evidence time |
| `tags` | string[] | Labels |
| `facts` | object[] | Structured sub-facts |
| `relations` | object[] | Links to other compiled entries |
| `meta` | object | Extra type-specific metadata |
|
### `entryType` values for v1

- `project`
- `system`
- `decision`
- `incident`
- `timeline_event`
- `person`
- `todo`

---

## `state` values

Mneme v1 should be explicit about memory quality.

| State | Meaning |
|---|---|
| `observed` | Directly supported by evidence |
| `inferred` | Reasonable synthesis from evidence, but not directly stated as-is |
| `stale` | Once true or likely true, but needs re-check |
| `contradicted` | Conflicts with stronger or newer evidence |
| `historical` | Kept for context, not current truth |
|
This is one of the key differences between raw evidence and compiled memory:
compiled memory is allowed to express status.

---

## `facts` array

`summary` is for fast reading.
`facts` is for structure.

Each fact should use a stable shape.

### Fact object

| Field | Type | Meaning |
|---|---|---|
| `key` | string | Fact name |
| `value` | string / number / boolean / object | Fact value |
| `state` | enum | Fact-level state |
| `evidenceRefs` | object[] | Supporting evidence refs |
|
### Example

```json
{
  "key": "deployPattern",
  "value": "nuxt generate -> tar -> scp to /var/www/bdeep/",
  "state": "observed",
  "evidenceRefs": [
    {
      "evidenceItemId": "evi:memory:MEMORY.md:54:sha256:example"
    }
  ]
}
```

---

## `relations` array

Relations let compiled memory link entries without flattening everything into prose.

### Relation object

| Field | Type | Meaning |
|---|---|---|
| `type` | enum | Relationship type |
| `targetEntryId` | string | Linked entry |
| `state` | enum | Confidence/state of the relation |
|
### Relation types for v1

- `depends_on`
- `related_to`
- `supersedes`
- `derived_from`
- `owned_by`
- `affects`

---

## Evidence refs in compiled entries

Compiled memory must keep evidence visible.

### EvidenceRef object

| Field | Type | Meaning |
|---|---|---|
| `evidenceItemId` | string | Reference to raw evidence item |
| `weight` | number | Optional ranking/support strength |
| `note` | string | Optional explanation |
|
V1 can survive with just `evidenceItemId`.
The extra fields are there so later compiler passes can rank or annotate support.

---

## Example — CompiledDocument

```json
{
  "id": "doc:compiled:projects",
  "kind": "projects",
  "title": "Compiled Projects",
  "generatedAt": "2026-04-03T13:00:00Z",
  "entryIds": [
    "cmp:project:bdeep-v2",
    "cmp:project:mneme"
  ],
  "sourceIds": [
    "src:memory:MEMORY.md:sha256:abc123",
    "src:daily-note:2026-04-02:sha256:def456"
  ]
}
```

## Example — CompiledEntry

```json
{
  "id": "cmp:project:bdeep-v2",
  "documentId": "doc:compiled:projects",
  "entryType": "project",
  "title": "bdeep v2",
  "summary": "Active fish-monitoring project with curated truth expected to come from PostgreSQL 18 rather than raw receiver rows.",
  "state": "observed",
  "updatedAt": "2026-04-03T13:00:00Z",
  "lastConfirmedAt": "2026-04-02T00:00:00Z",
  "tags": ["project", "fish-monitoring", "bdeep"],
  "facts": [
    {
      "key": "mainCheckout",
      "value": "/opt/work/bdeep",
      "state": "observed",
      "evidenceRefs": [
        { "evidenceItemId": "evi:memory:MEMORY.md:52:sha256:example" }
      ]
    },
    {
      "key": "truthLayer",
      "value": "curated PostgreSQL 18",
      "state": "observed",
      "evidenceRefs": [
        { "evidenceItemId": "evi:daily-note:2026-04-02:120-130:sha256:example" }
      ]
    }
  ],
  "relations": [
    {
      "type": "related_to",
      "targetEntryId": "cmp:system:windows-yibin-server",
      "state": "observed"
    }
  ],
  "evidenceRefs": [
    { "evidenceItemId": "evi:memory:MEMORY.md:50-60:sha256:example" },
    { "evidenceItemId": "evi:daily-note:2026-04-02:118-135:sha256:example" }
  ]
}
```

---


## Current implementation note

The current compiler implementation now emits both:
- structured JSONL (`documents.jsonl`, `entries.jsonl`)
- rendered markdown views (`projects.md`, `systems.md`, etc.)

That keeps the compiled layer machine-usable and agent-readable at the same time.

## v1 markdown rendering

Mneme can store structured JSON internally and still render markdown for agent readability.

Suggested mapping:
- one `CompiledDocument` -> one markdown file
- one `CompiledEntry` -> one section
- `summary` -> paragraph under heading
- `facts` -> bullet list
- `relations` -> short linked list
- `evidenceRefs` -> source block

That gives us both:
- human/agent-readable markdown
- stable machine-usable structure

---

## v1 storage shape

A practical v1 shape is:
- `compiled/documents.jsonl`
- `compiled/entries.jsonl`
- optional rendered markdown views in `compiled/*.md`

This lets Mneme:
- keep a stable structured layer
- regenerate markdown views cleanly
- diff compiled memory over time

---

## Minimum validity rules

A compiled entry is only valid if it has:
- `id`
- `documentId`
- `entryType`
- `title`
- `summary`
- `state`
- at least one `evidenceRef`
- `updatedAt`

If a compiled entry has no evidence refs, it is not Mneme memory.
It is just unsupported prose.

---

## Practical interpretation

In v1, Mneme should first compile these entry types well:
- `project`
- `system`
- `decision`
- `incident`
- `timeline_event`

That is enough to make Six's memory substantially more usable before chasing more ambitious graph/entity work.
