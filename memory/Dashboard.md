# FTE Dashboard

> Central hub for the FTE knowledge vault. Start here to navigate or orient context before executing any task.

---

## System Status

| Service | Port | Log |
|---------|------|-----|
| Frontend | [localhost:3000](http://localhost:3000) | `logs/frontend-dev.log` |
| Backend API | [localhost:8000/api/v1](http://localhost:8000/api/v1) | `logs/backend-dev.log` |
| MCP Server | localhost:8001 | `logs/mcp-server.log` |
| Executor | — | `logs/executor.log` |
| Watchers | — | `logs/watchers.log` |

**Health**: [localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)
**API Docs**: [localhost:8000/docs](http://localhost:8000/docs)

---

## Quick Actions

| Intent | Do This |
|--------|---------|
| Start all services | `bash scripts/start-fte.sh` |
| Create a task | POST `/api/v1/tasks/manual` or use dashboard UI |
| Retry a failed task | POST `/api/v1/tasks/{id}/retry` |
| Check task status | GET `/api/v1/tasks?status=need_action` |
| View logs live | `tail -f logs/<service>-dev.log` |

---

## Task Lifecycle

```
need_action → processing → done
                        ↘ failed  →  (retry)  →  need_action
```

**Pickup SLA**: within 10 seconds of creation
**Max retries**: 3 (env: `EXECUTOR_MAX_RETRIES`)

---

## Memory Index

### Owner Context
- [[preferences/email-style]] — Email tone and structure defaults
- [[tone/formal]] — Formal writing rules for client-facing comms

### Business Knowledge
- [[knowledge/product-pricing]] — Pricing tiers, discounts
- [[Company_Handbook]] — Full system reference (architecture, APIs, workflows)

### Clients
- [[clients/sample-client]] — Template / Acme Corp example
- *(Add new client profiles to `memory/clients/`)*

### System Logs
- `memory/logs/` — Watcher and executor event logs

---

## Specifications & Plans

| Artifact | Path |
|----------|------|
| Feature Spec | `specs/001-fte-task-executor/spec.md` |
| Architecture Plan | `specs/master/plan.md` |
| Task List | `specs/001-fte-task-executor/tasks.md` |
| Constitution | `.specify/memory/constitution.md` |
| Prompt History | `history/prompts/` |
| ADRs | `history/adr/` |

---

## Core Principles (Quick Ref)

| # | Principle | Rule |
|---|-----------|------|
| I | File-Based Execution | Every task MUST be a `.md` file in `/tasks/` |
| II | MCP Tool Isolation | No direct API calls from executor; use MCP only |
| III | Auditability | Every state transition MUST be logged |
| IV | Watcher-Driven Ingestion | Watchers create tasks; they do NOT execute them |
| V | Memory-Augmented Reasoning | Load relevant memory before every task |
| VI | Security by Default | JWT auth, no hardcoded secrets, rate limiting |

---

## Executor Memory Loading Guide

When executing a task, load memory in this order:

1. **Always load**: [[Company_Handbook]] (system reference)
2. **For email/communication tasks**: [[preferences/email-style]], [[tone/formal]]
3. **For client-facing tasks**: `memory/clients/<client-name>.md`
4. **For pricing/product questions**: [[knowledge/product-pricing]]
5. **Skip**: logs, unrelated client profiles

---

*Vault: `/mnt/d/hackathon-FTE/memory/` | Updated: 2026-02-24*
