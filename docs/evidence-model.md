# Mneme Evidence Model

Mneme needs one boring, stable answer to a simple question:

**What is the raw thing we actually know?**

This document defines the v1 evidence model.

## Goal

Give ingest, compile, retrieval, and maintenance one shared raw-memory shape.

Without this, every layer invents its own idea of "memory" and they drift immediately.

## Design rules

- **Evidence is raw, not inferred.**
- **Provenance is mandatory.**
- **Evidence is append-friendly and reviewable.**
- **Secrets may be redacted, but provenance must survive redaction.**
- **Compiled memory can summarize evidence, but evidence itself should not pretend to be summary.**

## Two-level model

Mneme v1 uses two layers:

1. **EvidenceSource** — where the evidence came from
2. **EvidenceItem** — the smallest fact-bearing unit we want to retrieve or compile

This keeps file/message/document metadata separate from the individual slices used for recall.

---

## EvidenceSource

Represents the origin container.

Examples:
- one `MEMORY.md` file
- one daily note file
- one chat transcript
- one repo file
- one web page fetch
- one PDF

### Required fields

| Field | Type | Meaning |
|---|---|---|
| `id` | string | Stable source identifier |
| `sourceType` | enum | Kind of source |
| `uri` | string | Canonical location or path |
| `capturedAt` | ISO timestamp | When Mneme captured or indexed it |
| `contentHash` | string | Hash of source content at capture time |
|
### Optional fields

| Field | Type | Meaning |
|---|---|---|
| `workspacePath` | string | Local path if applicable |
| `title` | string | Human-readable label |
| `sessionKey` | string | Origin session if source came from chat/session logs |
| `messageCount` | number | Useful for transcripts |
| `mimeType` | string | Content type |
| `meta` | object | Source-specific metadata |
|
### `sourceType` values for v1

- `memory_file`
- `daily_note`
- `session_transcript`
- `repo_file`
- `web_page`
- `pdf`
- `image`
- `manual_note`

---

## EvidenceItem

Represents one retrievable evidence slice.

Examples:
- one bullet in `MEMORY.md`
- one section heading + paragraph in a daily note
- one user/assistant message pair in a transcript
- one code comment block
- one extracted paragraph from a doc

### Required fields

| Field | Type | Meaning |
|---|---|---|
| `id` | string | Stable item identifier |
| `sourceId` | string | Parent `EvidenceSource.id` |
| `kind` | enum | Type of evidence slice |
| `text` | string | Raw text content used for recall/compilation |
| `capturedAt` | ISO timestamp | When Mneme captured/indexed this item |
| `provenance` | object | Where exactly it came from |
|
### Optional fields

| Field | Type | Meaning |
|---|---|---|
| `observedAt` | ISO timestamp | When the evidence was originally produced, if known |
| `actor` | object | Who produced it |
| `tags` | string[] | Lightweight labels |
| `secretRedacted` | boolean | Whether raw secrets were removed |
| `contentHash` | string | Hash of the item text |
| `meta` | object | Extra type-specific metadata |
|
### `kind` values for v1

- `memory_line`
- `note_bullet`
- `note_section`
- `chat_message`
- `chat_exchange`
- `doc_paragraph`
- `code_note`
- `incident_note`
- `decision_note`

---

## Provenance object

Provenance is required because Mneme is supposed to support trust, not vibes.

### Required provenance fields

| Field | Type | Meaning |
|---|---|---|
| `path` | string | Source-relative path or URI |
| `locatorType` | enum | How this item is located inside the source |
|
### Optional provenance fields

| Field | Type | Meaning |
|---|---|---|
| `lineStart` | number | Start line for text files |
| `lineEnd` | number | End line for text files |
| `headingPath` | string[] | Heading trail inside markdown/docs |
| `messageId` | string | Chat message id if applicable |
| `replyToId` | string | Reply chain link if applicable |
| `chunkIndex` | number | Chunk position for extracted docs |
|
### `locatorType` values for v1

- `line_range`
- `heading_section`
- `message_id`
- `chunk_index`
- `offset_range`

---

## Actor object

Only include this when it is known and useful.

### Fields

| Field | Type | Meaning |
|---|---|---|
| `id` | string | Stable actor id when known |
| `display` | string | Human-readable name |
| `role` | enum | `user`, `assistant`, `system`, `agent`, `external` |
|
---

## What does **not** belong in evidence

These belong later in compiled memory, not in raw evidence:

- inferred summaries presented as fact
- conflict resolution decisions
- staleness scoring
- contradiction status
- final entity linking
- promotion state

Evidence should say **what was seen**, not **what Mneme has concluded**.

---

## Redaction rule

If a secret appears in the original source:

- evidence may store a **redacted** text form
- provenance must still point back to the original source location
- `secretRedacted: true` should be set on the item

This preserves recall usefulness without turning memory into a credential dump.

---

## Example — EvidenceSource

```json
{
  "id": "src:memory:MEMORY.md:sha256:abc123",
  "sourceType": "memory_file",
  "uri": "file:///home/openclaw/.openclaw/workspace/MEMORY.md",
  "workspacePath": "MEMORY.md",
  "title": "Six long-term memory",
  "capturedAt": "2026-04-03T11:30:00Z",
  "contentHash": "sha256:abc123",
  "mimeType": "text/markdown"
}
```

## Example — EvidenceItem

```json
{
  "id": "evi:memory:MEMORY.md:20-24:sha256:def456",
  "sourceId": "src:memory:MEMORY.md:sha256:abc123",
  "kind": "memory_line",
  "text": "- **Memory search**: fixed on 2026-04-03 by switching from broken `local` embeddings to Gemini embeddings; semantic recall now works again",
  "capturedAt": "2026-04-03T11:30:00Z",
  "observedAt": "2026-04-03T00:00:00Z",
  "tags": ["memory", "infra"],
  "secretRedacted": false,
  "provenance": {
    "path": "MEMORY.md",
    "locatorType": "line_range",
    "lineStart": 7,
    "lineEnd": 7
  },
  "actor": {
    "id": "six",
    "display": "Six",
    "role": "agent"
  }
}
```

---

## v1 storage shape

Mneme does not need a database invention first.

A practical v1 storage shape is:
- `raw/sources.jsonl`
- `raw/items.jsonl`

One JSON object per line.

That is enough to:
- ingest deterministically
- diff changes
- rebuild indexes
- feed compiler/retrieval layers

---

## v1 minimum requirements

Any Mneme ingest pipeline is only valid if it produces:

- `EvidenceSource.id`
- `EvidenceItem.id`
- `sourceType`
- `kind`
- `text`
- `capturedAt`
- provenance with a real locator

If those are missing, the item is not reliable enough for Mneme.

---

## Practical interpretation

In v1, Mneme should treat:
- `MEMORY.md` bullets
- daily note bullets/sections
- session transcript messages

as the first-class evidence inputs.

That is enough to make Six's memory materially better before chasing fancier sources.
