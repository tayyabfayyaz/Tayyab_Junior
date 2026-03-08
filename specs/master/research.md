# Research: FTE – Fully Task Executor

**Date**: 2026-02-13
**Phase**: 0 — Outline & Research

---

## 1. Task File Format & Lifecycle Engine

**Decision**: Structured Markdown files with YAML-style metadata header, managed via filesystem directory transitions.

**Rationale**: Markdown is human-readable, version-controllable, and parseable by both Claude and standard tooling. Directory-based state (`need_action` → `processing` → `done` | `failed`) avoids database dependency for MVP while providing atomic state transitions via filesystem `move` operations.

**Alternatives considered**:
- **SQLite/PostgreSQL task queue**: Adds infrastructure complexity; file-based approach is simpler, auditable, and aligns with Constitution Principle I.
- **Redis-backed job queue (Celery/RQ)**: Overkill for single-executor MVP; introduces external dependency without clear benefit at current scale.
- **JSON task files**: Less human-readable than Markdown; harder to include freeform context sections.

---

## 2. FastAPI Backend Architecture

**Decision**: FastAPI (Python 3.11+) with Pydantic v2 models, uvicorn ASGI server, structured as a modular application with routers per domain (webhooks, tasks, auth).

**Rationale**: FastAPI provides automatic OpenAPI generation, async support for webhook handling, and native Pydantic validation — ideal for a webhook-heavy task management API. Python aligns with the Claude SDK ecosystem.

**Alternatives considered**:
- **Express.js/NestJS**: Would require context-switching between Python (executor scripts) and Node; unified Python stack reduces cognitive load.
- **Django REST Framework**: Heavier; FTE does not need ORM, admin panel, or session management at MVP stage.
- **Go (Gin/Echo)**: Faster runtime but slower development velocity; Python ecosystem better serves AI/LLM integration needs.

---

## 3. Next.js Frontend Architecture

**Decision**: Next.js 14+ (App Router) with TypeScript, TailwindCSS, and SWR/React Query for server state. API routes proxy to FastAPI backend.

**Rationale**: Next.js provides SSR for dashboard SEO (not critical but free), API routes for BFF pattern, and a mature component ecosystem. TypeScript ensures type safety across the frontend.

**Alternatives considered**:
- **Plain React SPA (Vite)**: No SSR, no API routes; would need a separate proxy layer.
- **Svelte/SvelteKit**: Smaller community; fewer component libraries for dashboard UIs.
- **HTMX + FastAPI templates**: Simpler but limited interactivity for real-time task status updates.

---

## 4. WhatsApp Integration Strategy

**Decision**: WhatsApp Business API via Meta Cloud API, with webhook verification endpoint in FastAPI. Messages parsed into structured task files using Claude for intent extraction.

**Rationale**: Meta Cloud API is the official channel, supports webhooks natively, and provides message templates for notifications. Claude-based intent parsing converts natural language commands into structured task metadata.

**Alternatives considered**:
- **Twilio WhatsApp API**: Additional cost layer; Meta Cloud API is direct and sufficient.
- **Unofficial WhatsApp libraries (Baileys)**: Violates WhatsApp ToS; risk of account ban.
- **Telegram Bot API**: Different platform; user specifically requires WhatsApp.

---

## 5. Email Integration Strategy

**Decision**: Gmail API with OAuth2 for reading; MCP email tool wrapping SMTP/Gmail API for sending. Gmail Push Notifications (Pub/Sub) for real-time detection, with polling fallback.

**Rationale**: Gmail API provides structured access to email metadata and content. Push notifications via Google Cloud Pub/Sub eliminate polling latency. OAuth2 is the only supported auth method for Gmail API.

**Alternatives considered**:
- **IMAP polling**: Higher latency, more complex connection management, less reliable for real-time needs.
- **Microsoft Graph API (Outlook)**: User context indicates Gmail; can be added as a second watcher later.
- **SendGrid/Mailgun for sending**: Adds external dependency; Gmail SMTP via MCP tool is sufficient for MVP.

---

## 6. Social Media Integration Strategy

**Decision**: LinkedIn API (OAuth2, Share API) and Twitter/X API v2 (OAuth 2.0 PKCE) accessed exclusively through MCP tools. Watcher uses polling with configurable intervals.

**Rationale**: Both platforms require OAuth2 and have rate limits that MCP tool isolation can enforce centrally. Polling is acceptable for social media where real-time is not critical (5-15 minute intervals).

**Alternatives considered**:
- **Buffer/Hootsuite API**: Adds third-party dependency and cost; direct API access provides more control.
- **Zapier/Make integration**: External automation; contradicts the self-contained system design.
- **Streaming APIs**: Twitter deprecated most streaming endpoints for free/basic tiers.

---

## 7. MCP Server Design

**Decision**: MCP server implemented in Python using the official MCP SDK (`mcp` package), exposing tools as registered functions with input/output schemas. Each tool wraps a single external API interaction.

**Rationale**: The MCP protocol is the native tool interface for Claude. Python implementation aligns with the backend stack. Tool registration with schemas enables input validation, output logging, and rate limiting at the protocol level.

**Alternatives considered**:
- **Custom REST-based tool server**: Would require building a custom tool-calling protocol; MCP is purpose-built.
- **LangChain tools**: Adds a heavy framework dependency; MCP is lighter and Claude-native.
- **Direct API calls with function wrappers**: Violates Constitution Principle II (MCP Tool Isolation).

---

## 8. Memory Layer (Obsidian Vault)

**Decision**: Obsidian-compatible Markdown vault stored at a configurable path. Claude reads memory files via MCP file tools before task execution. Memory organized by category: `preferences/`, `clients/`, `tone/`, `knowledge/`, `logs/`.

**Rationale**: Markdown files in a structured directory are version-controllable, human-editable, and directly readable by Claude. Obsidian compatibility allows the user to browse and manage memory via Obsidian's UI.

**Alternatives considered**:
- **Vector database (Pinecone/Chroma)**: Adds infrastructure; semantic search is not needed when memory is small and categorized.
- **SQLite knowledge base**: Less human-readable; harder for user to manually curate.
- **Redis key-value store**: Volatile unless persisted; lacks the rich document structure of Markdown.

---

## 9. Claude Executor Loop Design

**Decision**: A Python-based executor daemon that polls `/tasks/need_action/` at configurable intervals, picks one task at a time (FIFO by timestamp), moves it to `/processing/`, invokes Claude Code in autonomous mode with task context + memory context, and moves the result to `/done/` or `/failed/`.

**Rationale**: Single-threaded FIFO processing is simplest for MVP and avoids race conditions. Polling is reliable and debuggable. The executor is a thin orchestration layer — Claude does the reasoning.

**Alternatives considered**:
- **Filesystem watch (inotify/watchdog)**: More responsive but adds complexity; polling at 5-second intervals is sufficient for MVP.
- **Multi-threaded executor**: Risk of parallel MCP tool conflicts; sequential execution is safer for MVP.
- **Queue-based (RabbitMQ/SQS)**: Infrastructure overhead; file-based polling achieves the same result at current scale.

---

## 10. Containerization & Deployment Strategy

**Decision**: Docker Compose with 5 services (frontend, backend, executor, watchers, mcp-server). Each service has its own Dockerfile. Shared volume for `/tasks/` directory and memory vault.

**Rationale**: Docker Compose is the simplest multi-container orchestration for MVP. Shared volumes enable file-based communication between services without network overhead. Each service is independently rebuildable.

**Alternatives considered**:
- **Single monolith container**: Violates Constitution principle of independent deployability.
- **Kubernetes from day 1**: Over-engineering for MVP; Docker Compose can be graduated to K8s when scale demands it.
- **Serverless (Lambda/Cloud Functions)**: Incompatible with file-based task system and persistent executor loop.

---

## 11. Authentication & Security

**Decision**: OAuth2 with JWT tokens for API authentication. FastAPI `Depends()` injection for auth middleware. API keys for webhook verification (WhatsApp, GitHub). Environment variables via `.env` files (dotenv) for all secrets.

**Rationale**: OAuth2/JWT is industry standard for API auth. Webhook verification prevents unauthorized task injection. Environment-based secret management satisfies Constitution Principle VI without requiring a dedicated secrets manager at MVP.

**Alternatives considered**:
- **API key only**: Insufficient for user-facing frontend auth.
- **Session-based auth**: Stateful; complicates containerized deployment.
- **HashiCorp Vault/AWS Secrets Manager**: Right for production but over-engineering for MVP; `.env` + Docker secrets is sufficient.

---

## Summary of Technology Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| Frontend | Next.js + TypeScript + TailwindCSS | 14+ |
| Backend | FastAPI + Pydantic v2 + Uvicorn | Python 3.11+ |
| Executor | Python daemon + Claude Code SDK | Python 3.11+ |
| Watchers | Python async services | Python 3.11+ |
| MCP Server | Python MCP SDK | Latest |
| Task Storage | Filesystem (Markdown files) | N/A |
| Memory | Obsidian Vault (Markdown files) | N/A |
| Auth | OAuth2 + JWT | N/A |
| Deployment | Docker Compose | v2+ |
| Notifications | WhatsApp Business API + Email | N/A |
