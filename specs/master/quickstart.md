# Quickstart: FTE – Fully Task Executor

**Date**: 2026-02-13

---

## Prerequisites

- Docker & Docker Compose v2+
- Node.js 18+ (for frontend development)
- Python 3.11+ (for backend/executor development)
- Git
- WhatsApp Business Account (for WhatsApp integration)
- Google Cloud Project with Gmail API enabled (for email integration)

---

## 1. Clone & Configure

```bash
git clone <repo-url> fte
cd fte
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# Core
FTE_ENV=development
TASK_DIR=./tasks
MEMORY_DIR=./memory

# Auth
JWT_SECRET=<generate-a-secure-secret>
OAUTH_CLIENT_ID=<your-oauth-client-id>
OAUTH_CLIENT_SECRET=<your-oauth-client-secret>

# WhatsApp
WHATSAPP_VERIFY_TOKEN=<your-verify-token>
WHATSAPP_ACCESS_TOKEN=<meta-access-token>
WHATSAPP_PHONE_ID=<phone-number-id>

# Gmail
GMAIL_CLIENT_ID=<google-client-id>
GMAIL_CLIENT_SECRET=<google-client-secret>
GMAIL_PUBSUB_TOPIC=<pubsub-topic>

# Social Media
LINKEDIN_CLIENT_ID=<linkedin-client-id>
LINKEDIN_CLIENT_SECRET=<linkedin-client-secret>
TWITTER_API_KEY=<twitter-api-key>
TWITTER_API_SECRET=<twitter-api-secret>

# GitHub
GITHUB_WEBHOOK_SECRET=<github-webhook-secret>

# Claude
ANTHROPIC_API_KEY=<your-api-key>
```

---

## 2. Create Task Directories

```bash
mkdir -p tasks/need_action tasks/processing tasks/done tasks/failed
mkdir -p logs
mkdir -p memory/preferences memory/clients memory/tone memory/knowledge memory/logs
```

---

## 3. Start Services (Docker)

```bash
docker compose up --build
```

This starts:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

---

## 4. Verify Installation

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Create a manual test task
curl -X POST http://localhost:8000/api/v1/tasks/manual \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-jwt-token>" \
  -d '{
    "type": "general",
    "priority": "low",
    "instruction": "Say hello world.",
    "context": "Installation verification test."
  }'

# Check task was created
ls tasks/need_action/
```

---

## 5. Development Mode (without Docker)

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8000
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
python src/main.py
```

---

## 6. Test the Flow

1. Open the dashboard at http://localhost:3000
2. Create a manual task via the UI
3. Observe the task appear in `/tasks/need_action/`
4. Watch the executor pick it up (moves to `/processing/`)
5. See the result in `/tasks/done/` or `/tasks/failed/`
6. Check logs at `/logs/task-transitions.jsonl`

---

## Common Issues

| Issue | Solution |
|-------|---------|
| Port 8000 in use | Change `BACKEND_PORT` in `.env` |
| Task not picked up | Check executor container logs: `docker compose logs executor` |
| WhatsApp webhook fails | Verify `WHATSAPP_VERIFY_TOKEN` matches Meta configuration |
| Gmail auth error | Re-run OAuth2 flow; check token expiration |
