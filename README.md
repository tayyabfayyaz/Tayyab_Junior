# FTE – Fully Task Executor

An autonomous AI assistant system that monitors Email, WhatsApp, Social Media, and GitHub, converts events into structured task files, and executes them via Claude through MCP tools.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Frontend    │────▶│   Backend    │────▶│  Task Files  │
│  (Next.js)   │     │  (FastAPI)   │     │  (Markdown)  │
└─────────────┘     └──────────────┘     └──────┬──────┘
                           │                      │
                    ┌──────┴──────┐         ┌─────▼──────┐
                    │  Webhooks   │         │  Executor   │
                    │  (WA/Email/ │         │  (Claude)   │
                    │   GitHub)   │         └─────┬──────┘
                    └─────────────┘               │
                                            ┌─────▼──────┐
                    ┌─────────────┐         │ MCP Server  │
                    │  Watchers   │         │  (Tools)    │
                    │  (Email/    │         └─────────────┘
                    │   Social)   │
                    └─────────────┘
```

**5 Services**: Frontend, Backend, Executor, MCP Server, Watchers

## Prerequisites

- Docker & Docker Compose v2+
- Node.js 18+ (for frontend development)
- Python 3.11+ (for backend development)

## Quickstart

```bash
# 1. Configure
cp .env.example .env
# Edit .env with your API keys

# 2. Create directories
mkdir -p tasks/{need_action,processing,done,failed}
mkdir -p memory/{preferences,clients,tone,knowledge,logs}
mkdir -p logs

# 3. Start all services
docker compose up --build

# 4. Access
# Dashboard: http://localhost:3000
# API:       http://localhost:8000
# API Docs:  http://localhost:8000/docs
```

## Development Mode

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn backend.src.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Executor
```bash
cd executor
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m executor.src.main
```

## Task Lifecycle

```
Created → /tasks/need_action/  (pending)
       → /tasks/processing/    (executor picked up)
       → /tasks/done/          (success, result populated)
       → /tasks/failed/        (error, can retry)
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/health` | System health check |
| GET | `/api/v1/stats` | Task statistics |
| GET | `/api/v1/tasks` | List tasks (with filters) |
| GET | `/api/v1/tasks/{id}` | Get task details |
| POST | `/api/v1/tasks/manual` | Create manual task |
| POST | `/api/v1/tasks/{id}/retry` | Retry failed task |
| POST | `/api/v1/auth/login` | Authenticate |
| GET | `/api/v1/tasks/stream` | SSE real-time updates |
| POST | `/api/v1/webhooks/whatsapp` | WhatsApp webhook |
| POST | `/api/v1/webhooks/email` | Gmail push notification |
| POST | `/api/v1/webhooks/github` | GitHub webhook |

## Environment Variables

See `.env.example` for all required configuration.

## Project Structure

```
backend/          FastAPI backend (task CRUD, webhooks, auth)
executor/         Claude executor daemon (poll, execute, complete)
mcp-server/       MCP tool server (file, shell, email, social, whatsapp)
watchers/         Platform watchers (email, social, scheduler)
frontend/         Next.js dashboard (task management UI)
tasks/            Task file directories (need_action, processing, done, failed)
memory/           Knowledge vault (preferences, clients, tone, knowledge)
logs/             JSONL audit logs
```
