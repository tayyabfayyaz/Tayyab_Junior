# API Contracts: FTE – Fully Task Executor

**Date**: 2026-02-13
**Phase**: 1 — Design & Contracts

---

## Base Configuration

- **Base URL**: `http://localhost:8000/api/v1`
- **Auth**: Bearer JWT token (except webhook verification endpoints)
- **Content-Type**: `application/json`
- **Error Format**: `{ "detail": "string", "code": "string" }`

---

## 1. Task Management Endpoints

### GET /tasks

List tasks with optional filtering.

**Query Parameters**:

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| status | string | all | Filter: `need_action`, `processing`, `done`, `failed` |
| type | string | all | Filter by task type |
| priority | string | all | Filter by priority |
| limit | integer | 50 | Max results (1-100) |
| offset | integer | 0 | Pagination offset |
| sort | string | created_at:desc | Sort field and direction |

**Response 200**:
```json
{
  "tasks": [
    {
      "task_id": "2026-02-13-001",
      "type": "email_reply",
      "priority": "high",
      "source": "gmail",
      "status": "need_action",
      "created_at": "2026-02-13T10:30:00Z",
      "updated_at": "2026-02-13T10:30:00Z",
      "instruction_preview": "Draft a professional email reply..."
    }
  ],
  "total": 42,
  "limit": 50,
  "offset": 0
}
```

---

### GET /tasks/{task_id}

Get full task details.

**Response 200**:
```json
{
  "task_id": "2026-02-13-001",
  "type": "email_reply",
  "priority": "high",
  "source": "gmail",
  "status": "processing",
  "created_at": "2026-02-13T10:30:00Z",
  "updated_at": "2026-02-13T10:31:00Z",
  "retry_count": 0,
  "source_ref": "msg-abc123",
  "context": "Client asked about enterprise pricing.",
  "instruction": "Draft a professional email reply explaining pricing.",
  "constraints": "Formal tone. Mention enterprise tier.",
  "expected_output": "Email body text",
  "result": null,
  "error": null
}
```

**Response 404**: `{ "detail": "Task not found", "code": "TASK_NOT_FOUND" }`

---

### POST /tasks/manual

Create a task manually from the dashboard.

**Request Body**:
```json
{
  "type": "general",
  "priority": "medium",
  "instruction": "Research competitor pricing and summarize findings.",
  "context": "Q3 planning requires competitive analysis.",
  "constraints": "Bullet point format, max 500 words.",
  "expected_output": "Summary document"
}
```

**Response 201**:
```json
{
  "task_id": "2026-02-13-002",
  "status": "need_action",
  "created_at": "2026-02-13T11:00:00Z"
}
```

**Response 422**: Validation error (missing required fields)

---

### POST /tasks/{task_id}/retry

Re-queue a failed task.

**Response 200**:
```json
{
  "task_id": "2026-02-13-001",
  "status": "need_action",
  "retry_count": 1
}
```

**Response 400**: `{ "detail": "Task is not in failed state", "code": "INVALID_STATE" }`
**Response 400**: `{ "detail": "Max retries exceeded", "code": "MAX_RETRIES" }`

---

## 2. Webhook Endpoints

### POST /webhooks/whatsapp

WhatsApp Business API webhook receiver.

**Headers**: `X-Hub-Signature-256` (HMAC verification)

**Request Body** (from Meta):
```json
{
  "object": "whatsapp_business_account",
  "entry": [{
    "id": "BUSINESS_ID",
    "changes": [{
      "value": {
        "messages": [{
          "from": "PHONE_NUMBER",
          "text": { "body": "Reply to Ali about the pricing proposal." },
          "timestamp": "1707820200"
        }]
      }
    }]
  }]
}
```

**Response 200**: `{ "status": "received" }`
**Response 403**: `{ "detail": "Invalid signature", "code": "AUTH_FAILED" }`

---

### GET /webhooks/whatsapp

WhatsApp webhook verification (required by Meta).

**Query Parameters**: `hub.mode`, `hub.verify_token`, `hub.challenge`

**Response 200**: Returns `hub.challenge` value (plain text)
**Response 403**: Token mismatch

---

### POST /webhooks/email

Gmail push notification receiver (via Google Cloud Pub/Sub).

**Request Body**:
```json
{
  "message": {
    "data": "BASE64_ENCODED_DATA",
    "messageId": "MSG_ID",
    "publishTime": "2026-02-13T10:00:00Z"
  },
  "subscription": "projects/PROJECT/subscriptions/SUB"
}
```

**Response 200**: `{ "status": "received" }`

---

### POST /webhooks/github

GitHub webhook receiver.

**Headers**: `X-Hub-Signature-256`, `X-GitHub-Event`

**Response 200**: `{ "status": "received" }`
**Response 403**: `{ "detail": "Invalid signature", "code": "AUTH_FAILED" }`

---

## 3. System Endpoints

### GET /health

Health check for container orchestration.

**Response 200**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "services": {
    "executor": "running",
    "watchers": {
      "email": "active",
      "whatsapp": "active",
      "social": "active",
      "github": "active"
    },
    "mcp_server": "connected",
    "task_dirs": {
      "need_action": 3,
      "processing": 1,
      "done": 47,
      "failed": 2
    }
  }
}
```

---

### GET /stats

Task execution statistics.

**Query Parameters**: `period` (today, week, month, all)

**Response 200**:
```json
{
  "period": "today",
  "total_tasks": 15,
  "by_status": {
    "need_action": 3,
    "processing": 1,
    "done": 10,
    "failed": 1
  },
  "by_type": {
    "email_reply": 5,
    "social_post": 3,
    "whatsapp_reply": 4,
    "general": 3
  },
  "avg_execution_time_ms": 4200
}
```

---

## 4. Authentication Endpoints

### POST /auth/login

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "hashed_password"
}
```

**Response 200**:
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

**Response 401**: `{ "detail": "Invalid credentials", "code": "AUTH_FAILED" }`

---

### POST /auth/refresh

**Headers**: `Authorization: Bearer <refresh_token>`

**Response 200**:
```json
{
  "access_token": "eyJ...",
  "expires_in": 3600
}
```

---

## 5. MCP Tool Contracts

These are the tools exposed by the MCP server to the Claude Executor.

### email_send

**Input**:
```json
{
  "to": "recipient@example.com",
  "subject": "Re: Enterprise Pricing",
  "body": "Email body text...",
  "reply_to_message_id": "msg-abc123"
}
```

**Output**:
```json
{
  "status": "sent",
  "message_id": "sent-xyz789"
}
```

### social_post

**Input**:
```json
{
  "platform": "linkedin",
  "content": "Post content text...",
  "media_urls": []
}
```

**Output**:
```json
{
  "status": "published",
  "post_id": "li-post-123",
  "url": "https://linkedin.com/posts/..."
}
```

### social_reply

**Input**:
```json
{
  "platform": "twitter",
  "reply_to_id": "tweet-456",
  "content": "Reply text..."
}
```

**Output**:
```json
{
  "status": "published",
  "reply_id": "tweet-789"
}
```

### whatsapp_send

**Input**:
```json
{
  "to": "PHONE_NUMBER",
  "message": "Task completed successfully."
}
```

**Output**:
```json
{
  "status": "sent",
  "message_id": "wa-msg-123"
}
```

### file_read

**Input**:
```json
{
  "path": "memory/clients/ali.md"
}
```

**Output**:
```json
{
  "content": "# Ali\n\nEnterprise client since 2025...",
  "exists": true
}
```

### file_write

**Input**:
```json
{
  "path": "memory/logs/execution-summaries.md",
  "content": "## 2026-02-13\n\n- Replied to Ali's pricing email.",
  "mode": "append"
}
```

**Output**:
```json
{
  "status": "written",
  "bytes": 52
}
```

### shell_exec

**Input**:
```json
{
  "command": "git status",
  "working_dir": "/project",
  "timeout_ms": 30000
}
```

**Output**:
```json
{
  "stdout": "On branch main\nnothing to commit",
  "stderr": "",
  "exit_code": 0
}
```
