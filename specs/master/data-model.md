# Data Model: FTE – Fully Task Executor

**Date**: 2026-02-13
**Phase**: 1 — Design & Contracts

---

## 1. Task (Core Entity)

The fundamental unit of work in FTE. Represented as a Markdown file on disk.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| task_id | string | YES | Format: `YYYY-MM-DD-NNN` (date + sequential counter) |
| type | enum | YES | One of: `email_reply`, `email_draft`, `social_post`, `social_reply`, `whatsapp_reply`, `coding_task`, `spec_generation`, `general` |
| priority | enum | YES | One of: `critical`, `high`, `medium`, `low` |
| source | enum | YES | One of: `gmail`, `whatsapp`, `linkedin`, `twitter`, `github`, `frontend`, `scheduler` |
| status | enum | YES (implicit) | Determined by directory: `need_action`, `processing`, `done`, `failed` |
| created_at | ISO 8601 | YES | Timestamp of task file creation |
| updated_at | ISO 8601 | YES | Timestamp of last state transition |
| context | text | YES | Freeform background information for the task |
| instruction | text | YES | What the executor must do |
| constraints | text | NO | Tone, format, or behavioral restrictions |
| expected_output | text | NO | Description of desired output format |
| result | text | NO | Populated after execution (in `/done/` files) |
| error | text | NO | Populated on failure (in `/failed/` files) |
| retry_count | integer | NO | Number of retry attempts (default: 0) |
| source_ref | string | NO | External reference (email ID, message ID, PR URL) |

### File Format

```markdown
---
task_id: "2026-02-13-001"
type: email_reply
priority: high
source: gmail
created_at: "2026-02-13T10:30:00Z"
updated_at: "2026-02-13T10:30:00Z"
retry_count: 0
source_ref: "msg-abc123"
---

# Task: Reply to client pricing inquiry

## Context
Client Ali sent an email asking about enterprise pricing for the Q3 deal.

## Instruction
Draft a professional email reply explaining the enterprise tier pricing.

## Constraints
- Formal tone
- Mention enterprise tier benefits
- Keep under 200 words

## Expected Output
Email body text ready to send.
```

### State Transitions

```
[created] → /tasks/need_action/
     ↓ (executor picks up)
/tasks/processing/
     ↓ (execution completes)
/tasks/done/        ← success (result field populated)
/tasks/failed/      ← failure (error field populated, retry_count incremented)
     ↓ (if retryable)
/tasks/need_action/ ← re-queued with incremented retry_count
```

### Validation Rules
- `task_id` MUST be unique across all directories.
- `type` MUST be a recognized enum value.
- `priority` MUST be a recognized enum value.
- `context` and `instruction` MUST NOT be empty.
- `retry_count` MUST NOT exceed configurable max (default: 3).
- Files in `/done/` MUST have a non-empty `result` section.
- Files in `/failed/` MUST have a non-empty `error` section.

---

## 2. TaskLog (Audit Entity)

An append-only log entry recording every task state transition.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| timestamp | ISO 8601 | YES | When the transition occurred |
| task_id | string | YES | References the Task |
| from_status | enum | YES | Previous status directory |
| to_status | enum | YES | New status directory |
| actor | string | YES | Who/what triggered the transition (executor, watcher, user) |
| detail | text | NO | Additional context (error message, tool used) |

### Storage
Append-only log file at `/logs/task-transitions.jsonl` (one JSON object per line).

---

## 3. WatcherEvent (Ingestion Entity)

Raw event captured by a watcher before conversion to a Task.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| event_id | string | YES | Unique identifier |
| watcher_type | enum | YES | `email`, `whatsapp`, `social_linkedin`, `social_twitter`, `github`, `scheduler` |
| raw_payload | object | YES | Original event data from the platform |
| detected_at | ISO 8601 | YES | When the watcher detected the event |
| action_required | boolean | YES | Whether this event warrants a task |
| task_id | string | NO | Task ID if a task was created |

### Storage
`/logs/watcher-events.jsonl`

---

## 4. MemoryDocument (Knowledge Entity)

A document in the Obsidian Vault memory layer.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| path | string | YES | Relative path within the vault (e.g., `clients/ali.md`) |
| category | enum | YES | `preferences`, `clients`, `tone`, `knowledge`, `logs` |
| title | string | YES | Document title |
| content | text | YES | Markdown content |
| last_modified | ISO 8601 | YES | Last edit timestamp |
| tags | list[string] | NO | Searchable tags |

### Directory Structure

```
memory/
├── preferences/
│   ├── email-style.md
│   └── response-defaults.md
├── clients/
│   ├── ali.md
│   └── enterprise-accounts.md
├── tone/
│   ├── formal.md
│   └── casual.md
├── knowledge/
│   ├── product-pricing.md
│   └── company-faq.md
└── logs/
    └── execution-summaries.md
```

---

## 5. MCPToolInvocation (Audit Entity)

Records every MCP tool call for auditability.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| invocation_id | string | YES | Unique identifier |
| task_id | string | YES | Which task triggered this invocation |
| tool_name | string | YES | MCP tool identifier (e.g., `email_send`, `social_post`) |
| input_params | object | YES | Parameters passed to the tool |
| output | object | YES | Tool response |
| status | enum | YES | `success`, `error` |
| duration_ms | integer | YES | Execution time in milliseconds |
| timestamp | ISO 8601 | YES | When the tool was called |

### Storage
`/logs/mcp-invocations.jsonl`

---

## 6. User (Auth Entity)

The system owner/operator. Single-user for MVP.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| user_id | string | YES | Unique identifier |
| name | string | YES | Display name |
| email | string | YES | Primary email |
| whatsapp_number | string | NO | WhatsApp contact for notifications |
| oauth_tokens | object | YES | Encrypted OAuth2 tokens for connected services |
| preferences | object | NO | UI and notification preferences |

### Storage
`/config/user.json` (encrypted at rest)

---

## Entity Relationship Summary

```
User (1) ──owns──> Task (many)
Task (1) ──produces──> TaskLog (many)
Task (1) ──triggers──> MCPToolInvocation (many)
WatcherEvent (1) ──creates──> Task (0..1)
MemoryDocument (many) ──read by──> Task (many)
```
