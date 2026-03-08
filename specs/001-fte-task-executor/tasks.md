# Tasks: FTE – Fully Task Executor

**Input**: Design documents from `/specs/master/` and `/specs/001-fte-task-executor/`
**Prerequisites**: plan.md (loaded), spec.md (loaded), research.md (loaded), data-model.md (loaded), contracts/api-contracts.md (loaded)

**Tests**: Not explicitly requested in spec. Test tasks are NOT included.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `backend/src/`, `frontend/src/`, `executor/src/`, `mcp-server/src/`, `watchers/src/`

---

## Phase 1: Setup (Project Initialization)

**Purpose**: Create project structure, initialize all services, configure shared infrastructure.

- [x] T001 Create root project directories: `backend/`, `executor/`, `mcp-server/`, `watchers/`, `frontend/`, `tasks/`, `memory/`, `logs/`
- [x] T002 [P] Create `backend/requirements.txt` with FastAPI, Pydantic v2, Uvicorn, python-dotenv, python-jose[cryptography], python-multipart, pyyaml dependencies
- [x] T003 [P] Create `executor/requirements.txt` with anthropic, pyyaml, python-dotenv dependencies
- [x] T004 [P] Create `mcp-server/requirements.txt` with mcp, pyyaml, python-dotenv dependencies
- [x] T005 [P] Create `watchers/requirements.txt` with httpx, google-api-python-client, google-auth-oauthlib, pyyaml, python-dotenv dependencies
- [x] T006 [P] Initialize Next.js 14+ project with TypeScript and TailwindCSS in `frontend/` using `npx create-next-app`
- [x] T007 [P] Create `.env.example` at project root with all required environment variables (JWT_SECRET, ANTHROPIC_API_KEY, WHATSAPP_*, GMAIL_*, LINKEDIN_*, TWITTER_*, GITHUB_*)
- [x] T008 [P] Create `.gitignore` at project root with entries for `.env`, `__pycache__`, `node_modules`, `.next`, `*.pyc`, `venv/`
- [x] T009 Create task directory structure: `tasks/need_action/`, `tasks/processing/`, `tasks/done/`, `tasks/failed/` with `.gitkeep` files
- [x] T010 Create memory directory structure: `memory/preferences/`, `memory/clients/`, `memory/tone/`, `memory/knowledge/`, `memory/logs/` with `.gitkeep` files
- [x] T011 Create logs directory: `logs/` with `.gitkeep`

**Checkpoint**: All project directories initialized. Dependency manifests in place. Ready for foundational implementation.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented.

**CRITICAL**: No user story work can begin until this phase is complete.

- [x] T012 Create backend configuration loader in `backend/src/config.py` — read all env vars with defaults, expose as Pydantic Settings model
- [x] T013 Create Task Pydantic models in `backend/src/models/task.py` — TaskCreate, TaskResponse, TaskListResponse with all fields from data-model.md (task_id, type enum, priority enum, source enum, status, timestamps, context, instruction, constraints, expected_output, result, error, retry_count, source_ref)
- [x] T014 Create Task file parser in `backend/src/services/task_parser.py` — parse Markdown+YAML frontmatter task files into TaskResponse Pydantic models, handle malformed files gracefully
- [x] T015 Create Task file writer in `backend/src/services/task_writer.py` — generate structured Markdown task files with YAML frontmatter from TaskCreate input, auto-generate task_id (YYYY-MM-DD-NNN format), set created_at/updated_at timestamps
- [x] T016 Create Task lifecycle manager in `backend/src/services/task_engine.py` — implement directory-based state transitions (need_action→processing→done/failed), atomic file move operations, task listing per directory, task lookup by ID across all directories, JSONL transition logging to `logs/task-transitions.jsonl`
- [x] T017 Create FastAPI app entry point in `backend/src/main.py` — initialize FastAPI app with CORS middleware, include routers, configure lifespan events
- [x] T018 Create MCP server entry point in `mcp-server/src/main.py` — initialize MCP server with tool registry using official MCP SDK
- [x] T019 [P] Create MCP file_read tool in `mcp-server/src/tools/files.py` — accept path parameter, return file content or not-found error, log invocation to `logs/mcp-invocations.jsonl`
- [x] T020 [P] Create MCP file_write tool in `mcp-server/src/tools/files.py` — accept path, content, mode (write/append) parameters, write file, log invocation to `logs/mcp-invocations.jsonl`
- [x] T021 [P] Create MCP shell_exec tool in `mcp-server/src/tools/shell.py` — accept command, working_dir, timeout_ms parameters, execute subprocess, return stdout/stderr/exit_code, log invocation to `logs/mcp-invocations.jsonl`
- [x] T022 Create MCP invocation logger in `mcp-server/src/logger.py` — append-only JSONL logger that records invocation_id, task_id, tool_name, input_params, output, status, duration_ms, timestamp to `logs/mcp-invocations.jsonl`
- [x] T023 Create executor configuration in `executor/src/config.py` — polling interval, task directories, MCP server URL, Anthropic API key, max retries from env vars
- [x] T024 Create executor polling loop in `executor/src/polling.py` — scan `tasks/need_action/` at configurable interval, pick oldest file (FIFO by created_at), return file path or None
- [x] T025 Create executor memory loader in `executor/src/memory_loader.py` — read relevant memory documents from `memory/` vault based on task type and source, return concatenated context string scoped by category
- [x] T026 Create executor runner in `executor/src/runner.py` — receive task file path, parse task, load memory context, invoke Claude via Anthropic SDK with task instruction + context + memory, collect result, handle errors
- [x] T027 Create executor daemon entry point in `executor/src/main.py` — main loop that calls polling→pick→move to processing→run→move to done/failed, log all transitions, handle graceful shutdown
- [x] T028 Create health check endpoint in `backend/src/api/system.py` — GET /api/v1/health returning status of task directories (count per directory), GET /api/v1/stats returning task counts by status/type/source with period filter

**Checkpoint**: Foundation ready — task engine, MCP server (file tools), executor daemon, and health API all functional. User story implementation can begin.

---

## Phase 3: User Story 1 — Manual Task Creation & Execution (Priority: P1) MVP

**Goal**: End-to-end task lifecycle — dashboard creates task → executor picks up → AI executes → result visible.

**Independent Test**: Create a manual task via the API, verify it flows through need_action→processing→done, and result is retrievable.

### Implementation for User Story 1

- [x] T029 [US1] Create task CRUD router in `backend/src/api/tasks.py` — implement GET /api/v1/tasks (list with filters: status, type, priority, source, limit, offset, sort), GET /api/v1/tasks/{task_id} (detail), POST /api/v1/tasks/manual (create), POST /api/v1/tasks/{task_id}/retry (re-queue failed task). All endpoints use task_engine service for file operations.
- [x] T030 [US1] Register task and system routers in `backend/src/main.py` — import and include task router at `/api/v1` prefix, system router at `/api/v1`
- [x] T031 [US1] Create backend Dockerfile in `backend/Dockerfile` — Python 3.11 slim base, copy requirements.txt, pip install, copy src/, expose port 8000, CMD uvicorn
- [x] T032 [US1] Create executor Dockerfile in `executor/Dockerfile` — Python 3.11 slim base, copy requirements.txt, pip install, copy src/, CMD python main.py
- [x] T033 [US1] Create MCP server Dockerfile in `mcp-server/Dockerfile` — Python 3.11 slim base, copy requirements.txt, pip install, copy src/, CMD python main.py
- [x] T034 [US1] Create frontend API client in `frontend/src/services/api.ts` — typed fetch wrapper for all backend endpoints: listTasks(filters), getTask(id), createManualTask(data), retryTask(id), getHealth(), getStats()
- [x] T035 [US1] Create StatusBadge component in `frontend/src/components/StatusBadge.tsx` — color-coded badge for task status (need_action=yellow, processing=blue, done=green, failed=red)
- [x] T036 [US1] Create TaskCard component in `frontend/src/components/TaskCard.tsx` — display task summary (id, type, priority, source, status badge, instruction preview, timestamps)
- [x] T037 [US1] Create Navigation component in `frontend/src/components/Navigation.tsx` — sidebar or top nav with links to Dashboard, Tasks, and status indicator
- [x] T038 [US1] Create root layout in `frontend/src/app/layout.tsx` — TailwindCSS setup, Navigation component, main content area
- [x] T039 [US1] Create dashboard page in `frontend/src/app/page.tsx` — display task count cards per status (pending, processing, done, failed), recent tasks list, auto-refresh every 5 seconds using polling
- [x] T040 [US1] Create task list page in `frontend/src/app/tasks/page.tsx` — filterable task list (filter by status, type, source, priority), sortable columns, pagination, auto-refresh
- [x] T041 [US1] Create task detail page in `frontend/src/app/tasks/[id]/page.tsx` — full task view showing all fields (context, instruction, constraints, expected_output, result, error), retry button for failed tasks, auto-refresh
- [x] T042 [US1] Create TaskForm component in `frontend/src/components/TaskForm.tsx` — manual task creation form with fields: type (dropdown), priority (dropdown), instruction (textarea), context (textarea), constraints (textarea), expected_output (textarea), submit button that calls POST /api/v1/tasks/manual
- [x] T043 [US1] Create frontend Dockerfile in `frontend/Dockerfile` — Node 18 base, copy package.json, npm install, copy src/, npm run build, CMD npm start
- [x] T044 [US1] Create `docker-compose.yml` at project root — define services: frontend (port 3000), backend (port 8000), executor, mcp-server; shared volumes for tasks/, memory/, logs/; environment from .env file; health checks; depends_on ordering (executor depends on mcp-server, backend depends on task volumes)

**Checkpoint**: User Story 1 complete. Manual task creation via dashboard → executor pickup → AI execution → result visible in dashboard. Full lifecycle operational.

---

## Phase 4: User Story 2 — WhatsApp Command Execution (Priority: P2)

**Goal**: WhatsApp message triggers task creation, AI executes, completion notification sent back.

**Independent Test**: Send a WhatsApp message, verify task is created and completion notification arrives.

### Implementation for User Story 2

- [x] T045 [US2] Create webhook event models in `backend/src/models/events.py` — WhatsAppWebhookPayload, WhatsAppMessage, WhatsAppVerification Pydantic models matching Meta Cloud API schema from contracts
- [x] T046 [US2] Create WhatsApp intent parser in `watchers/src/whatsapp_handler.py` — accept raw WhatsApp message text, use Claude (via Anthropic SDK) to extract task type, priority, instruction, context, and constraints; return structured task data ready for task_writer
- [x] T047 [US2] Create webhook router in `backend/src/api/webhooks.py` — implement POST /api/v1/webhooks/whatsapp (verify X-Hub-Signature-256, parse payload, call whatsapp_handler to create task file in need_action/), GET /api/v1/webhooks/whatsapp (Meta verification challenge-response)
- [x] T048 [US2] Register webhook router in `backend/src/main.py` — include webhook router at `/api/v1` prefix
- [x] T049 [US2] Create MCP whatsapp_send tool in `mcp-server/src/tools/messaging.py` — accept to (phone number) and message parameters, call WhatsApp Business API to send message, log invocation
- [x] T050 [US2] Create notification service in `executor/src/notifications.py` — after task completion/failure, if task source is "whatsapp", compose summary message and call MCP whatsapp_send tool to notify owner
- [x] T051 [US2] Integrate notification service into executor runner in `executor/src/runner.py` — after moving task to done/failed, call notification service for WhatsApp-originated tasks
- [x] T052 [US2] Add ambiguous message handling in `watchers/src/whatsapp_handler.py` — if Claude cannot extract a clear instruction, reply via whatsapp_send asking for clarification instead of creating a malformed task
- [x] T053 [US2] Update `docker-compose.yml` — add watchers service, add WHATSAPP_* env vars, ensure watchers container has access to tasks/ volume

**Checkpoint**: User Story 2 complete. WhatsApp command → task creation → AI execution → WhatsApp notification. Both US1 and US2 independently functional.

---

## Phase 5: User Story 3 — Email Monitoring & Auto-Response (Priority: P3)

**Goal**: Gmail watcher detects emails, classifies them, creates tasks for action-required emails, AI drafts and sends replies.

**Independent Test**: Send test email to monitored inbox, verify classification, task creation, reply draft, and email sent.

### Implementation for User Story 3

- [x] T054 [US3] Create base watcher class in `watchers/src/base.py` — abstract base with start/stop lifecycle, configurable polling interval, JSONL event logging to `logs/watcher-events.jsonl`, health check method
- [x] T055 [US3] Create email watcher in `watchers/src/email_watcher.py` — extend base watcher, connect to Gmail API with OAuth2, poll for new messages (or receive Pub/Sub push), for each new email: classify as action-required or informational using Claude, if action-required: create task file in need_action/ with sender, subject, body, thread context; log watcher event
- [x] T056 [US3] Create Gmail Pub/Sub webhook endpoint in `backend/src/api/webhooks.py` — implement POST /api/v1/webhooks/email to receive Google Cloud Pub/Sub push notifications, decode base64 data, trigger email watcher processing
- [x] T057 [US3] Create MCP email_send tool in `mcp-server/src/tools/email.py` — accept to, subject, body, reply_to_message_id parameters, send email via Gmail API/SMTP, log invocation
- [x] T058 [US3] Create watchers main entry point in `watchers/src/main.py` — initialize and start all active watchers (email watcher for this phase), handle graceful shutdown
- [x] T059 [US3] Update `docker-compose.yml` — add GMAIL_* env vars to watchers and mcp-server services

**Checkpoint**: User Story 3 complete. Email arrives → classified → task created → AI drafts reply → email sent via MCP. US1, US2, and US3 all independently functional.

---

## Phase 6: User Story 4 — Social Media Management (Priority: P4)

**Goal**: Scheduled social media posts and automated comment/mention responses.

**Independent Test**: Trigger a scheduled post task, verify content generated and published. Simulate a comment, verify reply generated and posted.

### Implementation for User Story 4

- [x] T060 [US4] Create social media watcher in `watchers/src/social_watcher.py` — extend base watcher, poll LinkedIn API for comments/mentions and Twitter/X API for mentions/DMs at configurable intervals, create task files in need_action/ for each actionable event with comment context
- [x] T061 [US4] Create scheduler watcher in `watchers/src/scheduler.py` — extend base watcher, read cron-style schedule configuration, generate social_post tasks in need_action/ at scheduled times with content guidelines and target platform
- [x] T062 [US4] Create MCP social_post tool in `mcp-server/src/tools/social.py` — accept platform (linkedin/twitter), content, media_urls parameters, publish to the specified platform via API, return post_id and URL, log invocation
- [x] T063 [US4] Create MCP social_reply tool in `mcp-server/src/tools/social.py` — accept platform, reply_to_id, content parameters, publish reply to the specified platform via API, return reply_id, log invocation
- [x] T064 [US4] Register social and scheduler watchers in `watchers/src/main.py` — add social_watcher and scheduler to watcher initialization alongside email_watcher
- [x] T065 [US4] Update `docker-compose.yml` — add LINKEDIN_* and TWITTER_* env vars to watchers and mcp-server services

**Checkpoint**: User Story 4 complete. Scheduled posts published on time. Comments/mentions detected and replied to. US1–US4 all independently functional.

---

## Phase 7: User Story 5 — Task Dashboard & Visibility (Priority: P5)

**Goal**: Real-time dashboard with full task visibility, filtering, and intervention capabilities.

**Independent Test**: Open dashboard while tasks are processing, verify real-time status updates, filtering, and detail views.

### Implementation for User Story 5

- [x] T066 [US5] Add SSE (Server-Sent Events) endpoint in `backend/src/api/system.py` — GET /api/v1/tasks/stream that pushes task status change events to connected clients whenever a task transitions state
- [x] T067 [US5] Create useTaskStream hook in `frontend/src/services/useTaskStream.ts` — EventSource-based React hook that connects to SSE endpoint and updates local task state in real-time (replacing polling)
- [x] T068 [US5] Enhance dashboard page in `frontend/src/app/page.tsx` — replace polling with SSE-based real-time updates, add status count animations on change, add quick-filter chips for each status
- [x] T069 [US5] Enhance task list page in `frontend/src/app/tasks/page.tsx` — integrate SSE for real-time updates, add search by task ID or instruction text, improve filter UX with dropdown selectors
- [x] T070 [US5] Enhance task detail page in `frontend/src/app/tasks/[id]/page.tsx` — integrate SSE for live status changes, add execution timeline showing state transitions with timestamps, add MCP tool invocation log section

**Checkpoint**: User Story 5 complete. Dashboard shows real-time status updates via SSE, full filtering, search, and task detail with execution timeline. All 5 user stories independently functional.

---

## Phase 8: Production Hardening & Cross-Cutting Concerns

**Purpose**: Security, reliability, and operational readiness across all user stories.

- [x] T071 Create JWT auth middleware in `backend/src/middleware/auth.py` — verify Bearer token on protected endpoints, extract user claims, return 401 on invalid/expired tokens
- [x] T072 Create auth router in `backend/src/api/auth.py` — implement POST /api/v1/auth/login (validate credentials, return JWT access token), POST /api/v1/auth/refresh (issue new token from refresh token)
- [x] T073 Apply auth middleware to protected routes in `backend/src/main.py` — add auth dependency to task CRUD, stats, SSE endpoints; exclude webhook endpoints and health check
- [x] T074 Create rate limiting middleware in `backend/src/middleware/rate_limit.py` — configurable per-endpoint rate limits, apply to all webhook and API endpoints, return 429 on exceeded
- [x] T075 Add retry mechanism with exponential backoff in `executor/src/runner.py` — on task failure, check retry_count against max (default 3), if retriable: increment retry_count, move back to need_action/ with backoff delay; if exhausted: move to failed/
- [x] T076 Add high-risk action approval gate in `executor/src/runner.py` — before executing tasks flagged as high-risk (financial proposals, account modifications, bulk operations), send WhatsApp approval request via MCP whatsapp_send and pause execution until owner responds
- [x] T077 Create GitHub webhook handler in `watchers/src/github_handler.py` — receive GitHub webhook events (issues, PRs, reviews) via POST /api/v1/webhooks/github, verify X-Hub-Signature-256, create task files for actionable events (PR review requests, issue assignments)
- [x] T078 Add GitHub webhook endpoint in `backend/src/api/webhooks.py` — implement POST /api/v1/webhooks/github with signature verification, dispatch to github_handler
- [x] T079 Register GitHub watcher in `watchers/src/main.py` — add github_handler to watcher initialization
- [x] T080 Create login page in `frontend/src/app/login/page.tsx` — email/password form, call POST /api/v1/auth/login, store JWT in httpOnly cookie or localStorage, redirect to dashboard on success
- [x] T081 Add auth guard to frontend in `frontend/src/services/api.ts` — attach JWT to all API requests, redirect to login on 401, implement token refresh flow
- [x] T082 [P] Create sample memory documents — `memory/preferences/email-style.md` (owner's email tone), `memory/clients/sample-client.md` (client profile), `memory/tone/formal.md` (formal writing guide), `memory/knowledge/product-pricing.md` (pricing info)
- [x] T083 [P] Create `.env.example` with all environment variables documented with comments and placeholder values
- [x] T084 Update `docker-compose.yml` — add GITHUB_* env vars, configure restart policies (on-failure with max 3), add health check commands for each service, production-ready logging configuration
- [x] T085 Create root `README.md` — project overview, architecture diagram, prerequisites, quickstart (docker compose up), development mode instructions, environment variable reference

**Checkpoint**: Production-hardened. Auth, rate limiting, retries, approval gates, and GitHub integration all in place. System is deployment-ready.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Foundational — the MVP
- **US2 (Phase 4)**: Depends on Foundational + webhook router (T047 builds on backend from US1)
- **US3 (Phase 5)**: Depends on Foundational + base watcher class (T054)
- **US4 (Phase 6)**: Depends on Foundational + base watcher (T054 from US3)
- **US5 (Phase 7)**: Depends on US1 frontend (enhances existing pages)
- **Hardening (Phase 8)**: Depends on all user stories being functional

### User Story Dependencies

- **US1 (P1)**: Can start after Foundational — no dependencies on other stories
- **US2 (P2)**: Can start after Foundational — independent from US1 (backend already exists)
- **US3 (P3)**: Can start after Foundational — introduces base watcher class used by US4
- **US4 (P4)**: Depends on base watcher class from US3 (T054) — otherwise independent
- **US5 (P5)**: Depends on frontend pages from US1 (T039-T041) — enhances them with SSE

### Within Each User Story

- Models before services
- Services before API endpoints
- Backend before frontend
- Core implementation before integration

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel (T002-T008)
- Foundational: T019-T021 (MCP tools) in parallel; T024-T026 (executor modules) sequential
- US1: T034-T037 (frontend components) in parallel; T031-T033 (Dockerfiles) in parallel
- US2: T045-T046 in parallel with T049
- US3: T054-T055 sequential; T056-T057 in parallel
- US4: T060-T063 mostly parallel (different files)
- US5: T066-T070 sequential (SSE foundation then enhancements)
- Hardening: T071-T074 (auth+rate limit) sequential; T082-T083 in parallel

---

## Parallel Example: User Story 1

```bash
# Launch Dockerfiles in parallel:
Task: "Create backend Dockerfile in backend/Dockerfile"
Task: "Create executor Dockerfile in executor/Dockerfile"
Task: "Create MCP server Dockerfile in mcp-server/Dockerfile"
Task: "Create frontend Dockerfile in frontend/Dockerfile"

# Launch frontend components in parallel:
Task: "Create StatusBadge component in frontend/src/components/StatusBadge.tsx"
Task: "Create TaskCard component in frontend/src/components/TaskCard.tsx"
Task: "Create Navigation component in frontend/src/components/Navigation.tsx"
Task: "Create TaskForm component in frontend/src/components/TaskForm.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Create a manual task → verify full lifecycle
5. Deploy with Docker Compose

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 → Test independently → Deploy (MVP!)
3. Add US2 → WhatsApp commands work → Deploy
4. Add US3 → Email automation works → Deploy
5. Add US4 → Social media automation works → Deploy
6. Add US5 → Real-time dashboard → Deploy
7. Add Hardening → Production-ready → Final deploy

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: US1 (backend + frontend)
   - Developer B: US2 (WhatsApp) + US3 (Email)
   - Developer C: US4 (Social) — starts after US3's base watcher
3. US5 after US1 frontend is complete
4. Hardening as final team effort

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Total: 85 tasks across 8 phases
