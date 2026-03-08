# Implementation Plan: FTE – Fully Task Executor

**Branch**: `master` | **Date**: 2026-02-13 | **Spec**: [FTE.md](../../FTE.md)
**Input**: System documentation from `/FTE.md` and constitution from `.specify/memory/constitution.md`

---

## Summary

FTE is a production-grade autonomous AI assistant that monitors multiple platforms (Email, WhatsApp, Social Media, GitHub), converts actionable events into structured Markdown task files, and executes them via Claude Code through an MCP tool layer. The system uses a file-based task lifecycle (`need_action` → `processing` → `done` | `failed`) as its execution backbone, with a Next.js dashboard for visibility and a FastAPI backend for webhook ingestion and API management.

---

## Technical Context

**Language/Version**: Python 3.11+ (backend, executor, watchers, MCP server), TypeScript 5+ (frontend)
**Primary Dependencies**: FastAPI, Pydantic v2, Uvicorn, Next.js 14+, TailwindCSS, MCP Python SDK, Anthropic SDK
**Storage**: Filesystem (Markdown task files), JSONL (logs), JSON (config)
**Testing**: pytest (Python services), Jest + React Testing Library (frontend)
**Target Platform**: Linux containers (Docker), development on Windows/macOS/Linux
**Project Type**: Web application (frontend + backend + services)
**Performance Goals**: Task pickup latency <10s, API response <200ms p95, dashboard refresh <2s
**Constraints**: Single-user MVP, file-based task storage, all external calls via MCP, Docker Compose deployment
**Scale/Scope**: Single user, ~50-100 tasks/day, 5 watcher types, 7 MCP tools, 5 Docker services

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Status | Verification |
|---|-----------|--------|-------------|
| I | File-Based Task Execution | PASS | All tasks represented as `.md` files in lifecycle directories. No database task queue. |
| II | MCP Tool Isolation | PASS | Executor calls external APIs exclusively through MCP server tools. 7 tools defined in contracts. |
| III | Auditability & Transparency | PASS | TaskLog, WatcherEvent, MCPToolInvocation entities provide full audit trail. JSONL append-only logs. |
| IV | Watcher-Driven Ingestion | PASS | 5 independent watcher services create task files; watchers never execute. |
| V | Memory-Augmented Reasoning | PASS | Executor loads Obsidian Vault context before task execution. Memory scoped by category. |
| VI | Security by Default | PASS | OAuth2/JWT auth, webhook signature verification, encrypted tokens via `.env`, rate limiting, high-risk approval gate. |

**Gate result**: ALL PASS — proceed to Phase 0.

---

## 1. Executive Technical Strategy

### Vision
Build FTE as a **5-service Docker Compose system** where every external event becomes a structured Markdown task file, processed autonomously by Claude through an MCP tool layer, with full audit trail and dashboard visibility.

### Strategic Principles
1. **File-first**: The filesystem is the database. Task files are the source of truth.
2. **MCP-only**: Claude never touches external APIs directly. Every side-effect goes through MCP.
3. **Incremental delivery**: Each phase produces a deployable, testable increment.
4. **Single-user MVP**: Optimize for one power user before scaling.

### Technology Stack

| Layer | Technology | Justification |
|-------|-----------|---------------|
| Frontend | Next.js 14+ / TypeScript / TailwindCSS | SSR dashboard, API routes for BFF, mature ecosystem |
| Backend | FastAPI / Python 3.11+ / Pydantic v2 | Async webhooks, auto OpenAPI, Claude SDK alignment |
| Executor | Python daemon + Claude Code SDK | Thin orchestration loop; Claude does the reasoning |
| Watchers | Python async services | Same stack as backend; independent per platform |
| MCP Server | Python MCP SDK | Native Claude tool protocol; schema validation |
| Storage | Filesystem (Markdown + JSONL) | Human-readable, version-controllable, no DB dependency |
| Deployment | Docker Compose | Simplest multi-service orchestration for MVP |

---

## 2. Development Phases

### Phase 1: Foundation & Core Loop (MVP)

**Goal**: End-to-end task lifecycle — manual task creation → executor pickup → MCP execution → completion.

**Deliverables**:
- Task directory structure (`/tasks/{need_action,processing,done,failed}`)
- Task file schema (Markdown with YAML frontmatter)
- FastAPI backend with task CRUD endpoints
- Claude Executor daemon (poll → pick → execute → move)
- MCP Server with `file_read`, `file_write`, `shell_exec` tools
- Basic Next.js dashboard (list tasks, view details, create manual tasks)
- Docker Compose with 3 services (backend, executor, frontend)
- Health check and logging infrastructure

**Exit Criteria**:
- [ ] Manual task created via API → appears in `/need_action/`
- [ ] Executor picks task → moves to `/processing/` → executes → moves to `/done/`
- [ ] Failed task lands in `/failed/` with error context
- [ ] Dashboard displays all task states in real-time
- [ ] Task transition log entries written to JSONL

---

### Phase 2: Communication Watchers

**Goal**: Automated task creation from WhatsApp and Email events.

**Deliverables**:
- WhatsApp Business API webhook integration
- WhatsApp intent parsing (natural language → structured task)
- Gmail API watcher (push notifications via Pub/Sub)
- Email classification (action-required vs. informational)
- MCP tools: `email_send`, `whatsapp_send`
- Notification service (task completion → WhatsApp message)
- Docker Compose expanded to include watcher services

**Exit Criteria**:
- [ ] WhatsApp message "Reply to Ali about pricing" → task file created → email drafted → sent via MCP
- [ ] New Gmail email detected → classified → task created if action required
- [ ] Completion notification sent back via WhatsApp
- [ ] Webhook signature verification rejects unauthorized requests

---

### Phase 3: Social Media & GitHub

**Goal**: Automated social media management and GitHub monitoring.

**Deliverables**:
- LinkedIn watcher (comments, mentions)
- Twitter/X watcher (mentions, DMs)
- GitHub watcher (issues, PRs, reviews)
- MCP tools: `social_post`, `social_reply`
- Scheduler watcher (cron-based scheduled posts)
- Memory layer integration (Obsidian Vault)

**Exit Criteria**:
- [ ] LinkedIn comment → task → Claude generates reply → posted via MCP
- [ ] Scheduled social post → task → content generated → published
- [ ] GitHub PR review request → task → review generated
- [ ] Executor loads client profiles from memory before composing replies

---

### Phase 4: Production Hardening

**Goal**: Security, reliability, and operational readiness.

**Deliverables**:
- OAuth2/JWT authentication for dashboard
- Rate limiting on all webhook endpoints
- Retry mechanism with exponential backoff
- High-risk action approval gate (user confirmation via WhatsApp)
- Comprehensive error handling and recovery
- Task execution SLA monitoring
- Log aggregation and alerting
- Docker Compose production configuration
- `.env.example` and deployment documentation

**Exit Criteria**:
- [ ] Unauthenticated API requests rejected (401)
- [ ] Failed tasks auto-retry up to 3 times with backoff
- [ ] High-risk tasks prompt user for WhatsApp approval
- [ ] System recovers gracefully from service restarts
- [ ] All MCP tool invocations logged with timing

---

## 3. Module Breakdown

### Module 1: Task Engine (`backend/src/tasks/`)
- Task file parser (Markdown + YAML frontmatter)
- Task file writer (create structured `.md` files)
- Task lifecycle manager (directory transitions)
- Task ID generator (`YYYY-MM-DD-NNN`)
- Task validation (schema enforcement)

### Module 2: API Layer (`backend/src/api/`)
- Task CRUD router (`/api/v1/tasks/*`)
- Webhook router (`/api/v1/webhooks/*`)
- Auth router (`/api/v1/auth/*`)
- System router (`/api/v1/health`, `/api/v1/stats`)
- Middleware (auth, rate limiting, CORS, logging)

### Module 3: Executor (`executor/src/`)
- Polling loop (configurable interval)
- Task picker (FIFO by timestamp, respects priority)
- Memory loader (reads Obsidian Vault context)
- Claude invocation (task + memory → reasoning → tool calls)
- Result handler (move to `/done/` or `/failed/`)

### Module 4: MCP Server (`mcp-server/src/`)
- Tool registry (schema-based registration)
- Email tool (`email_send`)
- Social tools (`social_post`, `social_reply`)
- Messaging tool (`whatsapp_send`)
- File tools (`file_read`, `file_write`)
- Shell tool (`shell_exec`)
- Invocation logger

### Module 5: Watchers (`watchers/src/`)
- Email watcher (Gmail API + Pub/Sub)
- WhatsApp webhook handler
- Social media watchers (LinkedIn, Twitter)
- GitHub webhook handler
- Scheduler (cron-based task generation)
- Base watcher class (common polling/webhook patterns)

### Module 6: Frontend (`frontend/src/`)
- Dashboard page (task overview by status)
- Task detail page (full task file content)
- Manual task creation form
- Real-time status updates (polling/SSE)
- Auth pages (login)
- Layout and navigation

### Module 7: Memory Layer (`memory/`)
- Directory structure (preferences, clients, tone, knowledge, logs)
- Memory query interface (category + tag search)
- Memory update interface (append/overwrite with versioning)

### Module 8: Infrastructure (`docker/`, root configs)
- Dockerfiles per service
- Docker Compose configuration
- Environment variable management
- Shared volume configuration (tasks, memory, logs)
- Health check definitions

---

## 4. Service Responsibilities Matrix

| Service | Creates Tasks | Executes Tasks | Calls External APIs | Reads Memory | Writes Logs |
|---------|:---:|:---:|:---:|:---:|:---:|
| **Frontend** | via API | - | - | - | - |
| **Backend** | from webhooks | - | - | - | task transitions |
| **Executor** | - | YES | via MCP only | YES | task transitions, execution |
| **MCP Server** | - | - | YES | - | tool invocations |
| **Email Watcher** | YES | - | Gmail API (read only) | - | watcher events |
| **WhatsApp Watcher** | YES | - | - (webhook-based) | - | watcher events |
| **Social Watcher** | YES | - | Platform APIs (read only) | - | watcher events |
| **GitHub Watcher** | YES | - | - (webhook-based) | - | watcher events |
| **Scheduler** | YES | - | - | - | watcher events |

---

## 5. Dependency Graph

```
Phase 1 (Foundation)
├── Task File Schema ──────────────────────┐
├── Task Directory Structure ──────────────┤
├── Task Engine (parser, writer, lifecycle)─┤
│                                          ↓
├── FastAPI Backend ──── depends on ──── Task Engine
├── Claude Executor ──── depends on ──── Task Engine + MCP Server
├── MCP Server (file tools only) ─────── standalone
├── Next.js Frontend ──── depends on ──── Backend API
└── Docker Compose ──── depends on ──── all above

Phase 2 (Communication)
├── WhatsApp Webhook ──── depends on ──── Backend (webhook router)
├── Gmail Watcher ──── depends on ──── Task Engine
├── MCP email_send ──── depends on ──── MCP Server
├── MCP whatsapp_send ── depends on ──── MCP Server
└── Notification Service ── depends on ── MCP whatsapp_send

Phase 3 (Social & GitHub)
├── Social Watchers ──── depends on ──── Task Engine
├── GitHub Watcher ──── depends on ──── Backend (webhook router)
├── MCP social_post ──── depends on ──── MCP Server
├── Scheduler ──── depends on ──── Task Engine
└── Memory Layer ──── depends on ──── MCP file tools

Phase 4 (Hardening)
├── Auth (OAuth2/JWT) ──── depends on ──── Backend
├── Rate Limiting ──── depends on ──── Backend middleware
├── Retry Mechanism ──── depends on ──── Executor
├── Approval Gate ──── depends on ──── MCP whatsapp_send
└── Monitoring ──── depends on ──── Logging infrastructure
```

### Critical Path
`Task Schema → Task Engine → Executor + MCP Server → Backend API → Frontend`

All other modules (watchers, additional MCP tools, memory) extend this foundation without blocking it.

---

## 6. Risk & Mitigation Plan

| # | Risk | Impact | Probability | Mitigation |
|---|------|--------|-------------|------------|
| 1 | **WhatsApp Business API approval delays** | Phase 2 blocked for WhatsApp features | Medium | Implement with mock webhook first; apply for API access in parallel. Use Twilio sandbox for testing. |
| 2 | **Claude API rate limits or latency spikes** | Task execution backlog | Medium | Implement backpressure: pause polling when queue depth exceeds threshold. Add circuit breaker. |
| 3 | **File system race conditions** | Duplicate task processing or lost tasks | Low | Executor uses atomic file move operations. Single-threaded processing in MVP. File locking for multi-executor future. |
| 4 | **OAuth token expiration** | Gmail/Social watchers stop detecting events | Medium | Token refresh logic with expiration buffer. Alert on refresh failure. Fallback to polling with stored credentials. |
| 5 | **MCP tool failure cascades** | Single tool failure blocks all tasks of that type | Medium | Per-tool circuit breakers. Task retry with exponential backoff. Tool health status in dashboard. |
| 6 | **Memory context pollution** | Executor loads irrelevant context, degrading output quality | Low | Scope memory retrieval by task type + source. Limit context window budget per memory category. |
| 7 | **Docker volume permissions** | Services cannot read/write shared task directory | Low | Explicit UID/GID in Dockerfiles. Volume permissions set in compose file. CI test validates permissions. |

---

## 7. Deployment Strategy

### MVP (Docker Compose)

```yaml
services:
  frontend:     # Next.js on port 3000
  backend:      # FastAPI on port 8000
  executor:     # Python daemon (no exposed port)
  watchers:     # Python services (no exposed port)
  mcp-server:   # MCP SDK server (internal port)

volumes:
  tasks:        # Shared: /tasks/{need_action,processing,done,failed}
  memory:       # Shared: /memory/{preferences,clients,tone,knowledge,logs}
  logs:         # Shared: /logs/*.jsonl
```

### Deployment Steps
1. Build images: `docker compose build`
2. Configure: Copy `.env.example` → `.env`, fill credentials
3. Initialize: `mkdir -p tasks/{need_action,processing,done,failed} memory/{preferences,clients,tone,knowledge,logs} logs`
4. Start: `docker compose up -d`
5. Verify: `curl localhost:8000/api/v1/health`

### Production Evolution (Future)
- Docker Compose → Kubernetes with Helm charts
- Shared volumes → Network file system (NFS) or object storage adapter
- Single executor → Executor pool with task claiming (distributed lock)
- JSONL logs → ELK stack or Loki
- `.env` secrets → Kubernetes Secrets or Vault

---

## 8. Future Scalability Plan

### Multi-Agent Architecture
- Replace single executor with agent pool
- Each agent specializes by task type (email agent, social agent, coding agent)
- Task router assigns tasks to appropriate agent
- Agents share MCP server but have isolated memory contexts

### Priority Queue System
- Replace FIFO polling with priority-weighted queue
- Critical tasks preempt low-priority ones
- Queue depth monitoring with auto-scaling triggers

### Distributed Execution
- Kubernetes-based deployment with horizontal pod autoscaling
- Task directory replaced with distributed queue (Redis Streams or Kafka)
- MCP server scaled per tool type
- Geographic distribution for latency optimization

### Intelligence Layer
- AI self-improvement: executor reviews own failed tasks and adjusts approach
- Learning from user feedback on completed tasks
- Automatic memory updates based on interaction patterns
- Prompt optimization based on task success rates

### Additional Channels
- Voice command integration (speech-to-text → task file)
- Slack/Teams integration
- SMS gateway
- Calendar integration (auto-generate tasks from upcoming meetings)

---

## Project Structure

### Documentation (this feature)

```text
specs/master/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── api-contracts.md # Phase 1 output
└── tasks.md             # Phase 2 output (via /sp.tasks)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Environment configuration
│   ├── api/
│   │   ├── tasks.py         # Task CRUD router
│   │   ├── webhooks.py      # Webhook handlers
│   │   ├── auth.py          # Auth router
│   │   └── system.py        # Health, stats
│   ├── models/
│   │   ├── task.py          # Task Pydantic models
│   │   └── events.py        # Webhook event models
│   ├── services/
│   │   ├── task_engine.py   # File-based task lifecycle
│   │   ├── task_parser.py   # Markdown + YAML parser
│   │   └── task_writer.py   # Task file generator
│   └── middleware/
│       ├── auth.py          # JWT verification
│       └── rate_limit.py    # Rate limiting
├── tests/
│   ├── contract/
│   ├── integration/
│   └── unit/
├── Dockerfile
└── requirements.txt

executor/
├── src/
│   ├── main.py              # Executor daemon entry
│   ├── polling.py           # Task directory poller
│   ├── runner.py            # Claude invocation wrapper
│   └── memory_loader.py     # Obsidian Vault reader
├── tests/
├── Dockerfile
└── requirements.txt

mcp-server/
├── src/
│   ├── main.py              # MCP server entry
│   ├── tools/
│   │   ├── email.py         # email_send tool
│   │   ├── social.py        # social_post, social_reply tools
│   │   ├── messaging.py     # whatsapp_send tool
│   │   ├── files.py         # file_read, file_write tools
│   │   └── shell.py         # shell_exec tool
│   └── logger.py            # Invocation logger
├── tests/
├── Dockerfile
└── requirements.txt

watchers/
├── src/
│   ├── base.py              # Base watcher class
│   ├── email_watcher.py     # Gmail API watcher
│   ├── whatsapp_handler.py  # WhatsApp webhook consumer
│   ├── social_watcher.py    # LinkedIn + Twitter watcher
│   ├── github_handler.py    # GitHub webhook consumer
│   └── scheduler.py         # Cron-based task generator
├── tests/
├── Dockerfile
└── requirements.txt

frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx       # Root layout
│   │   ├── page.tsx         # Dashboard
│   │   ├── tasks/
│   │   │   ├── page.tsx     # Task list
│   │   │   └── [id]/
│   │   │       └── page.tsx # Task detail
│   │   └── login/
│   │       └── page.tsx     # Auth
│   ├── components/
│   │   ├── TaskCard.tsx
│   │   ├── TaskForm.tsx
│   │   ├── StatusBadge.tsx
│   │   └── Navigation.tsx
│   └── services/
│       └── api.ts           # Backend API client
├── tests/
├── Dockerfile
└── package.json

tasks/                       # Shared volume
├── need_action/
├── processing/
├── done/
└── failed/

memory/                      # Shared volume (Obsidian Vault)
├── preferences/
├── clients/
├── tone/
├── knowledge/
└── logs/

logs/                        # Shared volume
├── task-transitions.jsonl
├── watcher-events.jsonl
└── mcp-invocations.jsonl

docker-compose.yml
.env.example
```

**Structure Decision**: Web application structure selected — 5 independent service directories (backend, executor, mcp-server, watchers, frontend) with shared volumes for tasks, memory, and logs. Each service has its own Dockerfile and dependency manifest.

---

## Complexity Tracking

> No constitution violations detected. All principles satisfied by design.

| Principle | Design Choice | Compliance |
|-----------|--------------|------------|
| I. File-Based Task Execution | Markdown files in lifecycle directories | Direct implementation |
| II. MCP Tool Isolation | 7 MCP tools; executor has no direct API access | Direct implementation |
| III. Auditability & Transparency | 3 JSONL log types + dashboard | Direct implementation |
| IV. Watcher-Driven Ingestion | 5 independent watcher services | Direct implementation |
| V. Memory-Augmented Reasoning | Obsidian Vault loaded by executor before each task | Direct implementation |
| VI. Security by Default | OAuth2, JWT, webhook verification, rate limiting, approval gate | Direct implementation |
