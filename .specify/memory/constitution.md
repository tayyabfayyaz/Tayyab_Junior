<!--
  Sync Impact Report
  ==================
  Version change: 0.0.0 (template) → 1.0.0
  Bump rationale: MAJOR — first ratification; all principles newly defined.

  Modified principles:
    - [PRINCIPLE_1_NAME] → I. File-Based Task Execution
    - [PRINCIPLE_2_NAME] → II. MCP Tool Isolation
    - [PRINCIPLE_3_NAME] → III. Auditability & Transparency
    - [PRINCIPLE_4_NAME] → IV. Watcher-Driven Ingestion
    - [PRINCIPLE_5_NAME] → V. Memory-Augmented Reasoning
    - [PRINCIPLE_6_NAME] → VI. Security by Default

  Added sections:
    - Roles & Responsibilities
    - Non-Functional Requirements
    - Development Workflow

  Removed sections:
    - None (first ratification)

  Templates requiring updates:
    - .specify/templates/plan-template.md        — ⚠ pending (Constitution Check gates TBD per feature)
    - .specify/templates/spec-template.md         — ✅ no changes needed (generic template)
    - .specify/templates/tasks-template.md        — ✅ no changes needed (generic template)

  Deferred TODOs:
    - None
-->

# FTE (Fully Task Executor) Constitution

## Core Principles

### I. File-Based Task Execution

Every unit of work MUST be represented as a structured Markdown task file
following the lifecycle: `/tasks/need_action` → `/processing` → `/done` | `/failed`.

- Task files MUST contain: Task ID, Type, Priority, Source, Context,
  Instruction, Constraints, and Expected Output sections.
- The executor MUST NOT act on instructions that are not persisted as
  a task file. Verbal or in-memory-only commands are prohibited.
- Task files are the single source of truth for what was requested,
  what was executed, and what the outcome was.

**Rationale**: File-based execution ensures full reproducibility,
debuggability, and audit trail for every operation the system performs.

### II. MCP Tool Isolation

The Claude Executor MUST NEVER directly call external APIs (email,
social media, messaging). All external interactions MUST be routed
through MCP (Model Context Protocol) server tools.

- MCP tools include: email sender, social media poster, file editor,
  and shell command runner.
- Each MCP tool MUST log its invocation, inputs, and outputs.
- Adding a new external integration MUST require registering a new
  MCP tool; direct HTTP calls from the executor are forbidden.

**Rationale**: Routing all side-effects through MCP provides a single
control plane for security, rate limiting, and auditability.

### III. Auditability & Transparency

Every task execution MUST produce a traceable record. No silent
execution is permitted.

- Every task state transition (need_action → processing → done/failed)
  MUST be logged with a timestamp.
- The frontend dashboard MUST reflect real-time task status across
  all lifecycle stages.
- Failed tasks MUST retain the original instruction and append the
  error context for post-mortem analysis.

**Rationale**: The user MUST have full visibility into what the AI
assistant did, is doing, and has failed to do.

### IV. Watcher-Driven Ingestion

Platform monitoring MUST be performed by dedicated watcher services
that convert external events into task files.

- Supported watchers: Email (Gmail), WhatsApp (webhook), Social Media
  (LinkedIn/Twitter), GitHub, and Scheduler (cron-based).
- Watchers MUST NOT execute tasks themselves; their sole responsibility
  is to detect actionable events and create task files in `/tasks/need_action`.
- Each watcher MUST be independently deployable and restartable without
  affecting other watchers or the executor.

**Rationale**: Separating ingestion from execution enables independent
scaling, fault isolation, and platform-specific optimization.

### V. Memory-Augmented Reasoning

The Claude Executor MUST load relevant context from the memory layer
(Obsidian Vault) before executing any task.

- Memory MUST include: user preferences, client profiles, writing tone
  guidelines, project knowledge, and historical logs.
- Memory retrieval MUST be scoped to the task context to avoid
  irrelevant context pollution.
- Memory updates MUST be explicit and versioned; the executor MUST NOT
  silently mutate the memory store during task execution.

**Rationale**: Consistent, context-aware output quality depends on
the executor having access to accumulated organizational knowledge.

### VI. Security by Default

All external-facing interfaces MUST enforce authentication,
authorization, and input validation.

- OAuth2 MUST be used for user authentication.
- API tokens MUST be encrypted at rest and MUST NOT be hardcoded;
  environment variables or secret managers are required.
- High-risk actions (account deletion, bulk operations, financial
  transactions) MUST require explicit user approval before execution.
- Rate limiting MUST be applied to all webhook endpoints and
  external API calls.

**Rationale**: An autonomous system acting on behalf of the user
carries elevated risk; security MUST be the default posture, not
an afterthought.

## Roles & Responsibilities

| Role | Responsibility | Component |
|------|---------------|-----------|
| **User (Owner)** | Issues commands via WhatsApp or Frontend; approves high-risk actions; reviews task outcomes | WhatsApp, Next.js Dashboard |
| **Frontend (Next.js)** | Displays task dashboard, logs, and system status; enables manual task creation | Next.js App |
| **Backend (FastAPI)** | Receives webhooks; creates task files; serves task status API; handles auth | FastAPI Server |
| **Watchers** | Monitor platforms (Email, WhatsApp, Social, GitHub); create task files when action required | Watcher Services |
| **Task Manager** | Orchestrates task lifecycle; moves files between status directories | FastAPI / Executor |
| **Claude Executor** | Reads task files; loads memory; reasons and generates output; calls MCP tools | Claude Code (autonomous) |
| **MCP Server** | Exposes tool interfaces for external APIs; enforces isolation and logging | MCP Server |
| **Memory Layer** | Stores and serves user preferences, client profiles, tone, and project knowledge | Obsidian Vault |
| **Notification Service** | Sends completion/failure notifications back to the user | WhatsApp / Email |

## Non-Functional Requirements

### Performance
- Task execution MUST complete within the SLA defined per task type.
- Watcher polling intervals MUST be configurable and optimized to
  avoid unnecessary API consumption.

### Scalability
- Each component MUST be independently containerizable (Docker).
- The architecture MUST support horizontal scaling via container
  orchestration (Docker Compose for MVP; Kubernetes for production).

### Reliability
- Every task type MUST have a defined retry policy with exponential
  backoff.
- Failed tasks MUST be preserved in `/tasks/failed` with full error
  context; they MUST NOT be silently dropped.
- Watchers MUST implement health checks and automatic restart on
  failure.

### Auditability
- Every task state transition MUST be logged.
- MCP tool invocations MUST be logged with inputs, outputs, and
  timestamps.
- No component MUST perform silent execution without a corresponding
  log entry.

## Development Workflow

### Spec-Driven Development
1. All features MUST begin with a specification in `specs/<feature>/spec.md`.
2. Architecture decisions MUST be documented in `specs/<feature>/plan.md`.
3. Implementation tasks MUST be tracked in `specs/<feature>/tasks.md`.
4. Prompt history MUST be recorded under `history/prompts/`.

### Code Quality Gates
- All PRs MUST pass linting and formatting checks before merge.
- New endpoints MUST include integration tests.
- New MCP tools MUST include contract tests verifying input/output schemas.
- Secrets MUST NEVER be committed; `.env` files MUST be gitignored.

### Branching & Deployment
- Feature branches MUST follow the pattern `<issue-number>-<feature-name>`.
- The `main` branch MUST always be deployable.
- Docker Compose MUST be the deployment target for MVP.

## Governance

This constitution is the authoritative source for FTE project
principles and standards. It supersedes all other documentation
when conflicts arise.

### Amendment Procedure
1. Propose amendment via a PR modifying this file.
2. Amendment MUST include rationale and impact analysis.
3. Author approval is required for principle additions or removals.
4. All dependent templates MUST be checked for consistency after amendment.

### Versioning Policy
- **MAJOR**: Principle removal, redefinition, or backward-incompatible
  governance change.
- **MINOR**: New principle or section added; materially expanded guidance.
- **PATCH**: Clarifications, wording fixes, non-semantic refinements.

### Compliance Review
- Every PR MUST verify compliance with active principles.
- Constitution Check in `plan-template.md` MUST reference these
  principles by number (I through VI).
- Use `CLAUDE.md` for runtime development guidance.

**Version**: 1.0.0 | **Ratified**: 2026-02-13 | **Last Amended**: 2026-02-13
