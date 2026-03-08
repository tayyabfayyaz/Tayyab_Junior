# FTE Company Handbook

> **Purpose**: Single reference for the AI executor. Load this before any task requiring company context, communication, or system knowledge.

---

## 1. Product Overview

**FTE (Fully Task Executor)** is an autonomous AI assistant for a single owner. It monitors external platforms (Email, WhatsApp, Social Media, GitHub), converts events into structured task files, and executes them via Claude Code through MCP tools.

**Core value**: The owner spends < 15 min/day reviewing AI actions, down from 2+ hours of manual work.

---

## 2. Pricing & Plans

| Tier | Price | Tasks/mo | Integrations |
|------|-------|----------|-------------|
| Starter | $49/mo | 100 | Email only |
| Professional | $149/mo | 500 | All |
| Enterprise | $499+/mo (custom) | Unlimited | All + custom |

**Discounts**: 20% for annual billing. Multi-year: negotiable.

See full detail: [[knowledge/product-pricing]]

---

## 3. Communication Standards

### Email
- Professional yet approachable; direct and concise
- Open with a brief greeting; state purpose in sentence 1
- Use bullet points for details; close with a clear CTA
- See tone guide: [[preferences/email-style]]

### Formal Writing (client-facing, proposals)
- Complete sentences; no contractions
- Address by title + surname on first contact
- Include relevant data; passive voice sparingly
- See: [[tone/formal]]

### Writing Tone Decision Tree
1. External client? → Formal
2. Owner / internal? → Direct + concise
3. WhatsApp notification? → Brief, 1–2 sentences, emoji-free

---

## 4. Client Management

- Client profiles live in `memory/clients/`
- Always load the relevant client profile before drafting any communication
- Key fields per client: Company, Key Contacts, History, Preferences, SLA
- Sample profile: [[clients/sample-client]]

**SLA commitment**: 24-hour response for all client emails unless profile states otherwise.

---

## 5. System Architecture

### Services & Ports

| Service | Port | Start Command |
|---------|------|---------------|
| Backend (FastAPI) | 8000 | `uvicorn backend.src.main:app --reload` |
| Frontend (Next.js) | 3000 | `cd frontend && npm run dev` |
| MCP Server | 8001 | Started via executor dependency |
| Executor | — | `python3 -m executor.src.main` |
| Watchers | — | `python3 -m watchers.src.main` |

**Start all at once**: `bash scripts/start-fte.sh`

### Key URLs (local dev)
- Dashboard: http://localhost:3000
- API: http://localhost:8000/api/v1
- Health check: http://localhost:8000/api/v1/health
- API docs: http://localhost:8000/docs

---

## 6. Task Lifecycle

```
/tasks/need_action  →  /tasks/processing  →  /tasks/done
                                          ↘  /tasks/failed
```

**Task fields (required)**: `task_id`, `type`, `priority`, `source`, `context`, `instruction`, `constraints`, `expected_output`

**Task types**: `email_reply`, `social_post`, `whatsapp_reply`, `coding_task`, `general`

**Priorities**: `critical`, `high`, `medium`, `low`

**Sources**: `whatsapp`, `email`, `linkedin`, `twitter`, `github`, `scheduler`, `frontend`

**Retry policy**: Max 3 retries (configurable via `EXECUTOR_MAX_RETRIES`). Retry via `POST /api/v1/tasks/{id}/retry`.

---

## 7. API Reference

All endpoints under `/api/v1`. JWT Bearer token required (except `/auth/login`, `/health`, webhook endpoints).

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/login` | Get JWT token |
| GET | `/tasks` | List tasks (filters: status, type, priority, source) |
| GET | `/tasks/{id}` | Get task detail |
| POST | `/tasks/manual` | Create task from dashboard |
| POST | `/tasks/{id}/retry` | Re-queue failed task |
| POST | `/webhooks/whatsapp` | Incoming WhatsApp message |
| POST | `/webhooks/github` | Incoming GitHub event |
| GET | `/health` | System health (executor, watchers, task dirs) |

---

## 8. Memory Layer

The executor MUST load relevant memory before executing any task.

```
memory/
├── clients/          ← Client profiles (load by sender/company name)
├── knowledge/        ← Product info, pricing, FAQs
├── preferences/      ← Email style, communication defaults
├── tone/             ← Writing tone guides (formal, casual)
└── logs/             ← Watcher and system event logs
```

**Memory retrieval rule**: Match by task type and context keywords. Never load the entire vault—load only what's relevant to the task.

**Staleness check**: Documents > 90 days old should be flagged as potentially stale before use.

---

## 9. High-Risk Actions — Approval Required

The executor MUST pause and request owner approval before:

- Sending financial proposals or pricing quotes
- Account modifications or deletions
- Bulk email or social media operations (> 5 recipients / posts)
- Any action explicitly tagged `requires_approval: true` in the task file

Approval mechanism: Send a WhatsApp message to the owner with a summary of the pending action and await explicit "confirm" reply before proceeding.

---

## 10. Development Quick Reference

### Run dev servers
```bash
bash scripts/start-fte.sh
```

### View logs
```bash
tail -f logs/backend-dev.log
tail -f logs/frontend-dev.log
tail -f logs/executor.log
tail -f logs/watchers.log
```

### Environment
Copy `.env.example` → `.env`. Required secrets:
- `ANTHROPIC_API_KEY` — Claude API
- `JWT_SECRET` — Auth token signing
- `OWNER_EMAIL` / `OWNER_PASSWORD_HASH` — Dashboard login
- Platform tokens: `WHATSAPP_*`, `GMAIL_*`, `LINKEDIN_*`, `TWITTER_*`

### Tech Stack
- **Backend**: Python 3.11, FastAPI, uvicorn
- **Frontend**: Next.js 14, React 18, Tailwind CSS, TypeScript
- **AI**: Claude (`claude-sonnet-4-6` / `claude-opus-4-6`)
- **Transport**: MCP (Model Context Protocol) for all external actions
- **Deploy**: Docker Compose (MVP), Kubernetes (production)

### Branching convention
`<issue-number>-<feature-name>` (e.g. `001-fte-task-executor`)

---

*Last updated: 2026-02-24 | Version: 1.0.0*
