# FTE — Complete System Workflow

> **FTE (Fully Task Executor)** is an autonomous personal AI assistant that monitors platforms, converts events into structured tasks, executes them via Claude AI, and delivers results back — all with full transparency and human approval gates.

---

## Table of Contents

1. [System Architecture Overview](#1-system-architecture-overview)
2. [Component Map](#2-component-map)
3. [Task Lifecycle (State Machine)](#3-task-lifecycle-state-machine)
4. [Workflow 1 — Gmail Watcher → Task → Reply](#4-workflow-1--gmail-watcher--task--reply)
5. [Workflow 2 — WhatsApp Webhook → Task → Notification](#5-workflow-2--whatsapp-webhook--task--notification)
6. [Workflow 3 — Social Watcher → Task → Post](#6-workflow-3--social-watcher--task--post)
7. [Workflow 4 — GitHub Webhook → Coding Task](#7-workflow-4--github-webhook--coding-task)
8. [Workflow 5 — Manual Frontend Task](#8-workflow-5--manual-frontend-task)
9. [Workflow 6 — CEO Daily Report](#9-workflow-6--ceo-daily-report)
10. [Executor Deep-Dive](#10-executor-deep-dive)
11. [MCP Tool Layer](#11-mcp-tool-layer)
12. [Memory Vault](#12-memory-vault)
13. [Approval Gate Process](#13-approval-gate-process)
14. [Notification Routing](#14-notification-routing)
15. [Logging & Audit Trail](#15-logging--audit-trail)
16. [Environment & Configuration Reference](#16-environment--configuration-reference)
17. [Error Handling & Retry Policy](#17-error-handling--retry-policy)
18. [Directory Structure at Runtime](#18-directory-structure-at-runtime)

---

## 1. System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          INGESTION LAYER                                │
│                                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │ Gmail Watcher│  │ Social Watch │  │   WhatsApp   │  │  GitHub    │ │
│  │ (polls 15min)│  │ (polls 15min)│  │   Webhook    │  │  Webhook   │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └─────┬──────┘ │
│         │                 │                  │                │         │
│         └─────────────────┴──────────────────┴────────────────┘         │
│                                    │                                    │
│                                    ▼                                    │
│                         ┌──────────────────┐                           │
│                         │  FastAPI Backend  │                           │
│                         │  :8000            │                           │
│                         └──────────┬────────┘                           │
└────────────────────────────────────│────────────────────────────────────┘
                                     │ writes .md task files
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          FILE-BASED TASK QUEUE                          │
│                                                                         │
│   need_action/  →  awaiting_approval/  →  processing/  →  done/        │
│                                                          →  failed/     │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │ polls every 5s
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          EXECUTION LAYER                                │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                      Executor Daemon                             │  │
│  │                                                                  │  │
│  │  Poll → Pick Task → Load Memory → Build Prompt → Invoke Claude   │  │
│  │                              ↓                                   │  │
│  │                    Append Result to File                         │  │
│  │                              ↓                                   │  │
│  │               Move to /done or /failed                           │  │
│  │                              ↓                                   │  │
│  │                    Send Notification                             │  │
│  └─────────────────────────┬────────────────────────────────────────┘  │
│                             │                                           │
│                             ▼                                           │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                       MCP Server :8001                           │  │
│  │   email.py │ messaging.py │ social.py │ files.py │ shell.py      │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       PRESENTATION LAYER                                │
│                                                                         │
│  ┌─────────────────────┐   ┌──────────────────────────────────────┐    │
│  │  Next.js Dashboard  │   │        CEO Assistant                 │    │
│  │  :3000              │   │  Daily Report → CEO Email at 18:00   │    │
│  └─────────────────────┘   └──────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Component Map

| Component | Role | Port | Entry Point |
|-----------|------|------|-------------|
| **Gmail Watcher** | Polls Gmail API for unread important emails | — | `watchers/src/gmail_watcher.py` |
| **Social Watcher** | Polls LinkedIn/Twitter for mentions & DMs | — | `watchers/src/social_watcher.py` |
| **Backend API** | Webhooks, task CRUD, SSE streaming | 8000 | `backend/src/main.py` |
| **Executor** | Polls tasks, invokes Claude, writes results | — | `executor/src/main.py` |
| **MCP Server** | Isolated tool layer for external APIs | 8001 | `mcp_server/src/main.py` |
| **Frontend** | Web dashboard for tasks, approvals, reports | 3000 | `frontend/src/app/page.tsx` |
| **CEO Assistant** | Generates & emails daily executive report | — | `ceo_assistant/src/main.py` |

---

## 3. Task Lifecycle (State Machine)

```
                          ┌─────────────────┐
                          │  Event Detected  │
                          │  (Watcher/Webhook│
                          │  /Frontend)      │
                          └────────┬─────────┘
                                   │
                          Task file created
                                   │
                    ┌──────────────▼──────────────┐
                    │                             │
                    ▼                             ▼
           ┌──────────────┐             ┌──────────────────┐
           │ need_action/ │             │awaiting_approval/│
           │ (auto tasks) │             │ (sensitive tasks) │
           └──────┬───────┘             └────────┬─────────┘
                  │                              │
                  │                     User approves/rejects
                  │                              │
                  │                    ┌─────────┴──────────┐
                  │                    │                    │
                  │                    ▼                    ▼
                  │             ┌─────────────┐     ┌─────────────┐
                  │             │ need_action │     │   REJECTED  │
                  │             │ (moved here)│     │ (deleted or │
                  │             └──────┬──────┘     │ archived)   │
                  │                    │             └─────────────┘
                  └───────────────┐   │
                                  ▼   ▼
                           ┌─────────────┐
                           │ processing/ │  ← Executor picks task
                           └──────┬──────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │                           │
                    ▼                           ▼
             ┌──────────┐               ┌──────────────┐
             │  done/   │               │   failed/    │
             │ (success)│               │  (error +    │
             └──────────┘               │  retry ≤ 3)  │
                                        └──────┬───────┘
                                               │
                                    User retries from frontend
                                               │
                                               ▼
                                        need_action/
```

**Status Definitions:**

| Status | Directory | Description |
|--------|-----------|-------------|
| `need_action` | `tasks/need_action/` | Ready for executor to pick up |
| `awaiting_approval` | `tasks/awaiting_approval/` | Requires human approval before execution |
| `processing` | `tasks/processing/` | Currently being executed by Claude |
| `done` | `tasks/done/` | Successfully completed |
| `failed` | `tasks/failed/` | Execution failed; eligible for retry |

---

## 4. Workflow 1 — Gmail Watcher → Task → Reply

This is the primary automated inbound workflow.

```
Step 1: WATCHER POLLS GMAIL
───────────────────────────
Gmail Watcher (watchers/src/gmail_watcher.py)
  │
  ├── Every 15 minutes:
  │     gmail_service.py fetches unread "important" emails via Gmail API
  │     Checks gmail_watcher_state.json for already-processed message IDs
  │
  ├── For each NEW email:
  │     Extract: sender, subject, body, message_id, thread_id
  │     Determine: action_required = True/False
  │
  └── Logs watcher event → logs/watcher-events.jsonl
        {event_id, watcher_type:"gmail", detected_at, action_required, task_id}

Step 2: TASK FILE CREATED
──────────────────────────
task_writer.py generates Markdown task file:

  tasks/awaiting_approval/2026-02-28-001.md
  ┌──────────────────────────────────────────┐
  │ ---                                      │
  │ task_id: "2026-02-28-001"               │
  │ type: "email_reply"                      │
  │ priority: "high"                         │
  │ source: "gmail"                          │
  │ created_at: "2026-02-28T10:00:00Z"      │
  │ source_ref: "<msg123@gmail.com>"         │
  │ ---                                      │
  │                                          │
  │ ## Context                               │
  │ From: alice@client.com                   │
  │ Subject: Pricing Inquiry                 │
  │ Thread-ID: <thread456>                   │
  │ [email body]                             │
  │                                          │
  │ ## Instruction                           │
  │ Draft a professional email reply...      │
  │                                          │
  │ ## Constraints                           │
  │ Formal tone, mention ROI benefits...     │
  │                                          │
  │ ## Expected Output                       │
  │ Email body text (plain text, no HTML)    │
  └──────────────────────────────────────────┘

Step 3: HUMAN APPROVAL (Frontend)
───────────────────────────────────
Frontend polls GET /api/v1/tasks?status=awaiting_approval
User reviews task context and instruction
User clicks Approve → POST /api/v1/tasks/2026-02-28-001/approve

Backend (task_engine.py):
  - Moves file: awaiting_approval/ → need_action/
  - Logs transition: {from: awaiting_approval, to: need_action}

Step 4: EXECUTOR PICKS TASK
─────────────────────────────
executor/src/main.py polling loop (every 5 seconds):
  polling.py scans tasks/need_action/ for oldest .md file
  Moves: need_action/2026-02-28-001.md → processing/2026-02-28-001.md
  Logs transition: {from: need_action, to: processing}

Step 5: MEMORY LOAD
─────────────────────
runner.py → memory_loader.py
  Task type = "email_reply" → loads:
    memory/preferences/   (user preferences, reply style)
    memory/clients/       (client profile for alice@client.com)
    memory/tone/          (formal/informal tone guidelines)

Step 6: CLAUDE INVOCATION
──────────────────────────
runner.py builds prompt:
  [System]: You are a professional email assistant...
  [Memory context]: Client profile, tone guidelines, preferences
  [Task context]: Subject, sender, original email body
  [Instruction]: Draft a professional email reply...
  [Constraints]: Formal tone, mention ROI...

Calls: claude-haiku-4-5-20251001 (max_tokens=4096)
       Gemini fallback if Anthropic unavailable

Step 7: RESULT APPENDED
─────────────────────────
runner.py appends to task file:

  ## Result
  Dear Alice,

  Thank you for your inquiry about our enterprise pricing...
  [Full AI-generated email body]

  Generated at: 2026-02-28T10:05:00Z
  Model: claude-haiku-4-5-20251001

Step 8: TASK COMPLETED
────────────────────────
Executor moves: processing/ → done/
Logs transition: {from: processing, to: done, detail: "Execution successful"}

Step 9: EMAIL SENT
────────────────────
notifications.py detects source = "gmail"
  gmail_service.send_email(
    to = "alice@client.com",
    subject = "Re: Pricing Inquiry",
    body = [result from task file],
    thread_id = "<thread456>"
  )

Also sends WhatsApp notification to OWNER_PHONE:
  "✅ Task 2026-02-28-001 completed: email_reply to alice@client.com"

Step 10: FRONTEND UPDATES
──────────────────────────
Frontend SSE stream (GET /api/v1/tasks/stream) pushes update
Task detail page shows: Status=done, Result=[email body]
```

---

## 5. Workflow 2 — WhatsApp Webhook → Task → Notification

```
Step 1: WHATSAPP MESSAGE RECEIVED
───────────────────────────────────
Meta Platform → POST /api/v1/webhooks/whatsapp
Backend verifies HMAC-SHA256 signature with WHATSAPP_VERIFY_TOKEN

webhooks.py → whatsapp_handler.py:
  Parse message body
  Extract: sender_phone, message_text, timestamp
  Detect intent: type (email_reply/social_post/general), priority

Step 2: TASK CLASSIFICATION
─────────────────────────────
Intent detection maps message text to:
  TaskType: whatsapp_reply / email_reply / social_post / general
  TaskPriority: critical / high / medium / low
  TaskSource: whatsapp

Step 3: TASK FILE WRITTEN
──────────────────────────
task_writer.py generates:
  tasks/need_action/2026-02-28-002.md   (or awaiting_approval/ if sensitive)

  ---
  task_id: "2026-02-28-002"
  type: "whatsapp_reply"
  priority: "medium"
  source: "whatsapp"
  source_ref: "+1234567890"
  ---

  ## Context
  From: +1234567890
  Message: "Can you schedule a meeting with John for tomorrow?"

  ## Instruction
  Reply to the WhatsApp message with confirmation and next steps.

Step 4 → 8: EXECUTOR PROCESSES (same as Workflow 1, Steps 4–8)

Step 9: WHATSAPP REPLY SENT
─────────────────────────────
notifications.py detects source = "whatsapp"
  Calls Meta WhatsApp API:
    POST https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_ID}/messages
    {
      "to": "+1234567890",
      "type": "text",
      "text": {"body": "[AI-generated reply]"}
    }
  Uses: WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_ID
```

---

## 6. Workflow 3 — Social Watcher → Task → Post

```
Step 1: SOCIAL WATCHER POLLS
──────────────────────────────
social_watcher.py (every 15 min):

  LinkedIn:
    GET /v2/socialActions (mentions, comments, DMs)
    GET /v2/shares (engagement on posts)

  Twitter/X:
    GET /2/mentions/timeline
    GET /2/dm_conversations

  Checks processed event IDs to avoid duplicates

Step 2: TASK CREATED
─────────────────────
For each new mention/comment:
  Creates: tasks/awaiting_approval/2026-02-28-003.md
  Type: "social_reply" or "social_post"

  ## Context
  Platform: LinkedIn
  Author: Bob Smith (@bobsmith)
  Post: "Loved your article on AI automation! How does FTE handle..."

  ## Instruction
  Craft a thoughtful, engaging reply that adds value to the conversation.

  ## Constraints
  Professional tone, ≤280 chars for Twitter, mention key benefits,
  do not make promises about unreleased features.

Step 3: APPROVAL → EXECUTOR (same flow)

Step 4: SOCIAL POST PUBLISHED
───────────────────────────────
notifications.py detects source = "linkedin" or "twitter"

  LinkedIn:
    POST https://api.linkedin.com/v2/socialActions/{activity_id}/comments
    Authorization: Bearer {LINKEDIN_ACCESS_TOKEN}

  Twitter/X:
    POST https://api.twitter.com/2/tweets
    (OAuth 1.0a with TWITTER_API_KEY + ACCESS_TOKEN)

  Sanitization applied:
    - Strip preamble ("Here is a reply:", "Sure, here's...")
    - Strip markdown formatting (**, __, ##)
    - Enforce character limits (280 for Twitter)
    - Remove trailing whitespace
```

---

## 7. Workflow 4 — GitHub Webhook → Coding Task

```
Step 1: GITHUB EVENT RECEIVED
───────────────────────────────
GitHub → POST /api/v1/webhooks/github
Backend verifies HMAC-SHA256 with GITHUB_WEBHOOK_SECRET

github_handler.py parses event:
  - issue.opened → create spec_generation task
  - pull_request.review_requested → create coding_task
  - push (to main) → create general audit task

Step 2: TASK CREATED
─────────────────────
tasks/need_action/2026-02-28-004.md
  ---
  type: "coding_task"
  source: "github"
  source_ref: "PR#42"
  ---

  ## Context
  Repository: org/repo
  PR Title: "Add user authentication"
  PR Body: [description]
  Files Changed: [list]

  ## Instruction
  Review the PR for security issues, code quality, and spec alignment.

  ## Constraints
  Focus on auth flows, input validation, SQL injection risks.

Step 3: EXECUTOR (Memory: knowledge/)
  Loads: memory/knowledge/ (project architecture, coding standards)

Step 4: RESULT
  Claude generates code review / implementation spec
  Result appended to task file

Step 5: NOTIFICATION
  Owner notified via WhatsApp with task summary
```

---

## 8. Workflow 5 — Manual Frontend Task

```
Step 1: USER FILLS FORM
─────────────────────────
Frontend: http://localhost:3000 → "Create Task" button → TaskForm

  Fields:
    Type:         [email_reply / social_post / coding_task / general / ...]
    Priority:     [critical / high / medium / low]
    Context:      [background information]
    Instruction:  [what Claude should do]
    Constraints:  [rules and limitations]

Step 2: API CALL
─────────────────
POST /api/v1/tasks/manual
{
  "type": "general",
  "priority": "medium",
  "context": "Monthly newsletter planning",
  "instruction": "Draft a subject line and outline for the February newsletter",
  "constraints": "Fun tone, tech audience, max 500 words"
}

Step 3: TASK FILE CREATED
──────────────────────────
Backend generates task_id: YYYY-MM-DD-NNN (auto-incremented)
task_engine.py writes file to need_action/ (general tasks auto-proceed)
or awaiting_approval/ (if type is social_post/email_reply)

Step 4 → 8: EXECUTOR PROCESSES (standard flow)

Step 5: VIEW RESULT
────────────────────
Frontend: Tasks List → click task → detail page
GET /api/v1/tasks/2026-02-28-005

Shows: status=done, result=[AI output], execution time
```

---

## 9. Workflow 6 — CEO Daily Report

```
Step 1: SCHEDULER FIRES (18:00 UTC daily)
──────────────────────────────────────────
ceo_assistant/src/main.py
  APScheduler triggers report_generator.py at REPORT_TIME

Step 2: AGGREGATE TASK DATA
─────────────────────────────
report_generator.py:
  Scans all task directories for today's tasks
  Counts: total, done, failed, by_type, by_source
  Reads result sections from completed task files
  Identifies top failures with error messages

Step 3: CLAUDE GENERATES NARRATIVE
────────────────────────────────────
Invokes Claude with raw stats + task summaries:
  "Generate an executive report for today's AI assistant activity..."

Claude produces structured markdown:
  - Executive Summary (3 bullet points)
  - Task Breakdown (table by type/source)
  - Wins (top 3 successful outcomes)
  - Issues (failures with root cause)
  - Recommendations (next actions)

Step 4: REPORT SAVED
──────────────────────
reports/2026-02-28.md
  ---
  report_id: "2026-02-28"
  generated_at: "2026-02-28T18:00:00Z"
  total_tasks: 15
  completed: 12
  failed: 2
  pending: 1
  ---

  # CEO Daily Report — February 28, 2026
  [Full narrative...]

Step 5: EMAIL SENT TO CEO
──────────────────────────
mailer.py:
  gmail_service.send_email(
    to = CEO_EMAIL,
    subject = "FTE Daily Report — Feb 28, 2026",
    body = [report markdown]
  )

Step 6: VIEWABLE ON DASHBOARD
───────────────────────────────
GET /api/v1/reports → list all reports
GET /api/v1/reports/2026-02-28 → report detail
Frontend: http://localhost:3000/reports/2026-02-28
```

---

## 10. Executor Deep-Dive

The executor is the heart of the system. Here is the exact execution sequence:

```
executor/src/main.py — Main Loop
─────────────────────────────────

while True:
  sleep(EXECUTOR_POLL_INTERVAL_SECONDS)  # default: 5s

  task_file = polling.pick_next_task(tasks/need_action/)
  if not task_file:
    continue

  ┌─────────────────────────────────────────────────────┐
  │ runner.py → execute_task(task_file)                 │
  │                                                     │
  │  1. PARSE                                           │
  │     Read task file (YAML frontmatter + Markdown)    │
  │     Extract: task_id, type, source, context,        │
  │              instruction, constraints, source_ref   │
  │                                                     │
  │  2. MOVE TO PROCESSING                              │
  │     task_engine.transition(need_action → processing)│
  │     Log: task-transitions.jsonl                     │
  │                                                     │
  │  3. LOAD MEMORY                                     │
  │     memory_loader.load(task_type, task_source)      │
  │     Returns: List[str] of relevant memory docs      │
  │                                                     │
  │  4. BUILD PROMPT                                    │
  │     system_prompt = "You are a personal AI         │
  │                      assistant for [OWNER]..."      │
  │     user_prompt = memory_context                    │
  │                 + "\n\n## Task\n" + task_content    │
  │                                                     │
  │  5. INVOKE AI                                       │
  │     try:                                            │
  │       result = _invoke_anthropic(prompt)            │
  │       # claude-haiku-4-5-20251001, max_tokens=4096  │
  │     except:                                         │
  │       result = _invoke_gemini(prompt)  # fallback   │
  │                                                     │
  │  6. WRITE RESULT                                    │
  │     Append "## Result\n{result}" to task file       │
  │     Update: updated_at timestamp in YAML            │
  │                                                     │
  │  7. TRANSITION STATE                                │
  │     task_engine.transition(processing → done)       │
  │     Log: task-transitions.jsonl                     │
  │                                                     │
  │  8. SEND NOTIFICATION                               │
  │     notifications.notify(task)                      │
  └─────────────────────────────────────────────────────┘

  On Exception:
    Append "## Error\n{traceback}" to task file
    Increment retry_count in YAML
    if retry_count >= MAX_RETRIES (3):
      transition(processing → failed)
    else:
      transition(processing → need_action)  # re-queue
    Log failure transition
```

---

## 11. MCP Tool Layer

All external API calls from Claude are routed through the MCP server for isolation, logging, and auditability. Claude never directly calls external services.

```
┌─────────────────────────────────────────────────────────────────┐
│                     MCP Server (port 8001)                      │
│                                                                 │
│  Tool: email.py                                                 │
│    send_email(to, subject, body, thread_id=None)                │
│    → Gmail API (OAuth2)                                         │
│    → Logs: {tool:"email", to, subject, status, timestamp}       │
│                                                                 │
│  Tool: messaging.py                                             │
│    send_whatsapp(phone, message)                                 │
│    → Meta Graph API v18.0                                       │
│    → Logs: {tool:"messaging", phone[-4:], status, timestamp}    │
│                                                                 │
│  Tool: social.py                                                │
│    post_linkedin(text, activity_id=None)                        │
│    post_twitter(text, reply_to=None)                            │
│    → LinkedIn API v2 / Twitter API v2                           │
│    → Logs: {tool:"social", platform, chars, status, timestamp}  │
│                                                                 │
│  Tool: files.py                                                 │
│    read_file(path)                                              │
│    write_file(path, content)                                    │
│    → Sandboxed to TASK_DIR and MEMORY_DIR                       │
│    → Logs: {tool:"files", op, path, size, timestamp}            │
│                                                                 │
│  Tool: shell.py                                                 │
│    execute(command, cwd=None)                                   │
│    → Sandboxed shell execution                                  │
│    → Logs: {tool:"shell", cmd, exit_code, timestamp}            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 12. Memory Vault

The memory vault provides context to Claude for better, personalized responses.

```
memory/
├── preferences/          → User's communication preferences
│   └── preferences.md      (reply style, signature, scheduling preferences)
│
├── clients/              → Client profiles
│   ├── acme-corp.md        (company, contacts, relationship history)
│   └── john-smith.md       (individual profile, communication style)
│
├── tone/                 → Writing tone guidelines
│   └── tone-guide.md       (formal/informal rules, vocabulary, examples)
│
├── knowledge/            → Domain knowledge & project context
│   ├── product-overview.md
│   ├── pricing-tiers.md
│   └── tech-stack.md
│
├── logs/                 → Historical summaries (auto-populated)
│   └── monthly-summary.md
│
├── gmail_token.json      → Gmail OAuth2 refresh token (encrypted)
├── linkedin_token.json   → LinkedIn OAuth2 token
└── gmail_watcher_state.json → Last processed message IDs
```

**Memory Loading Rules (memory_loader.py):**

| Task Type | Memory Loaded |
|-----------|---------------|
| `email_reply` | preferences, clients, tone |
| `email_draft` | preferences, clients, tone |
| `social_post` | tone, knowledge |
| `social_reply` | tone, knowledge |
| `whatsapp_reply` | preferences, clients |
| `coding_task` | knowledge |
| `spec_generation` | knowledge |
| `general` | knowledge, preferences |

---

## 13. Approval Gate Process

Sensitive tasks land in `awaiting_approval/` before execution.

```
Tasks requiring approval:
  ✓ email_reply   (writes on your behalf)
  ✓ social_post   (public-facing content)
  ✓ social_reply  (public-facing content)

Tasks that auto-proceed:
  ✓ general       (internal only)
  ✓ coding_task   (local code review)
  ✓ spec_generation (internal artifact)

Approval via Frontend:
  GET  /api/v1/tasks?status=awaiting_approval
  POST /api/v1/tasks/{id}/approve  → moves to need_action/
  POST /api/v1/tasks/{id}/reject   → archives/deletes task

Approval via WhatsApp (future):
  Bot asks: "New email task from alice@client.com. Approve? Reply YES/NO"
  YES → moves to need_action
  NO  → archives task
```

---

## 14. Notification Routing

After task completion, the executor automatically notifies the right channel:

```
notifications.py — Routing Logic
──────────────────────────────────

if source == "gmail":
  gmail_service.send_email(
    to   = task.context["From"],
    body = task.result,
    thread_id = task.context["Thread-ID"]
  )

elif source == "whatsapp":
  POST https://graph.facebook.com/v18.0/{PHONE_ID}/messages
  {to: task.source_ref, text: {body: task.result}}

elif source in ["linkedin", "twitter"]:
  social.py MCP tool → publish response

# Always notify owner
whatsapp.send(WHATSAPP_OWNER_PHONE,
  f"✅ Task {task_id} [{task.type}] completed\n"
  f"Preview: {task.result[:100]}..."
)

# On failure
whatsapp.send(WHATSAPP_OWNER_PHONE,
  f"❌ Task {task_id} [{task.type}] failed\n"
  f"Error: {task.error[:100]}...\n"
  f"Retry count: {task.retry_count}/3"
)
```

---

## 15. Logging & Audit Trail

Every action in the system is logged for full auditability.

```
logs/
├── task-transitions.jsonl    → Every status change
└── watcher-events.jsonl      → Every event detected

task-transitions.jsonl entry:
{
  "timestamp": "2026-02-28T10:00:00Z",
  "task_id": "2026-02-28-001",
  "from_status": "need_action",
  "to_status": "processing",
  "actor": "executor",
  "detail": ""
}

watcher-events.jsonl entry:
{
  "event_id": "evt_abc12345",
  "watcher_type": "gmail",
  "detected_at": "2026-02-28T09:58:00Z",
  "action_required": true,
  "task_id": "2026-02-28-001",
  "source_ref": "<msg123@gmail.com>"
}

Backend also streams real-time events via SSE:
  GET /api/v1/tasks/stream  (Content-Type: text/event-stream)
  Pushes: {task_id, status, updated_at} on every transition
```

---

## 16. Environment & Configuration Reference

```bash
# ── AI Providers ──────────────────────────────────────────────
ANTHROPIC_API_KEY=sk-ant-...          # Claude API key (required)
GEMINI_API_KEY=...                    # Gemini fallback (optional)

# ── Executor ──────────────────────────────────────────────────
EXECUTOR_POLL_INTERVAL_SECONDS=5      # Task polling frequency
EXECUTOR_MAX_RETRIES=3                # Max retries before failed
MCP_SERVER_URL=http://mcp-server:8001 # MCP tool endpoint

# ── Paths ─────────────────────────────────────────────────────
TASK_DIR=./tasks                      # Task file directories
MEMORY_DIR=./memory                   # Knowledge vault
LOG_DIR=./logs                        # Audit logs
REPORTS_DIR=./reports                 # CEO reports

# ── Authentication ────────────────────────────────────────────
JWT_SECRET=change-me-in-production    # JWT signing secret
OWNER_EMAIL=owner@example.com         # System owner email
OWNER_PASSWORD_HASH=...               # bcrypt hash

# ── WhatsApp ──────────────────────────────────────────────────
WHATSAPP_VERIFY_TOKEN=...             # Meta webhook verify token
WHATSAPP_ACCESS_TOKEN=...             # Meta permanent access token
WHATSAPP_PHONE_ID=...                 # Meta phone number ID
WHATSAPP_OWNER_PHONE=+1234567890      # Owner's WhatsApp number

# ── Gmail ─────────────────────────────────────────────────────
GMAIL_CLIENT_ID=...                   # Google OAuth client ID
GMAIL_CLIENT_SECRET=...               # Google OAuth client secret
GMAIL_MONITORED_EMAIL=you@gmail.com   # Inbox to monitor

# ── LinkedIn ──────────────────────────────────────────────────
LINKEDIN_CLIENT_ID=...
LINKEDIN_CLIENT_SECRET=...
LINKEDIN_ACCESS_TOKEN=...

# ── Twitter/X ─────────────────────────────────────────────────
TWITTER_API_KEY=...
TWITTER_API_SECRET=...
TWITTER_ACCESS_TOKEN=...
TWITTER_ACCESS_SECRET=...

# ── GitHub ────────────────────────────────────────────────────
GITHUB_WEBHOOK_SECRET=...             # Webhook HMAC secret

# ── CEO Assistant ─────────────────────────────────────────────
CEO_EMAIL=ceo@example.com             # Report recipient
REPORT_TIME=18:00                     # Daily report time (UTC)

# ── Backend ───────────────────────────────────────────────────
BACKEND_PORT=8000
CORS_ORIGINS=http://localhost:3000

# ── Frontend ──────────────────────────────────────────────────
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

---

## 17. Error Handling & Retry Policy

```
Retry Logic (executor/src/runner.py):
──────────────────────────────────────

MAX_RETRIES = 3 (configurable via EXECUTOR_MAX_RETRIES)

Attempt 1: execute task
  → Success: move to done/
  → Failure: retry_count=1, re-queue to need_action/
              wait: 30 seconds before re-pick

Attempt 2: execute task
  → Success: move to done/
  → Failure: retry_count=2, re-queue to need_action/
              wait: 60 seconds (exponential backoff)

Attempt 3: execute task
  → Success: move to done/
  → Failure: retry_count=3, move to failed/
              Notify owner via WhatsApp
              Task stays in failed/ indefinitely

Manual Retry via Frontend:
  POST /api/v1/tasks/{id}/retry
  → Resets retry_count=0
  → Moves: failed/ → need_action/
  → Clears Error section from file

Error Types Captured:
  - AI API timeout / rate limit → retry
  - MCP tool failure (email send) → retry
  - Task file parse error → failed (no retry)
  - Memory load failure → continue with empty context
  - Notification failure → log warning, task still marked done
```

---

## 18. Directory Structure at Runtime

```
/mnt/d/hackathon-FTE/
│
├── tasks/                          ← RUNTIME: Task file queue
│   ├── need_action/                  Executor picks from here
│   │   └── 2026-02-28-007.md
│   ├── awaiting_approval/            Waiting for human
│   │   └── 2026-02-28-008.md
│   ├── processing/                   Currently executing
│   │   └── 2026-02-28-006.md
│   ├── done/                         Completed tasks
│   │   ├── 2026-02-28-001.md
│   │   └── ...
│   └── failed/                       Failed tasks (retryable)
│       └── 2026-02-28-003.md
│
├── memory/                         ← PERSISTENT: Context vault
│   ├── preferences/
│   │   └── preferences.md
│   ├── clients/
│   │   ├── acme-corp.md
│   │   └── john-smith.md
│   ├── tone/
│   │   └── tone-guide.md
│   ├── knowledge/
│   │   ├── product-overview.md
│   │   └── tech-stack.md
│   ├── logs/
│   ├── gmail_token.json
│   ├── linkedin_token.json
│   └── gmail_watcher_state.json
│
├── logs/                           ← RUNTIME: Audit logs (append-only)
│   ├── task-transitions.jsonl
│   └── watcher-events.jsonl
│
├── reports/                        ← RUNTIME: CEO daily reports
│   ├── 2026-02-28.md
│   └── 2026-02-27.md
│
├── backend/                        ← SOURCE: FastAPI API
├── executor/                       ← SOURCE: Claude executor daemon
├── watchers/                       ← SOURCE: Platform monitors
├── frontend/                       ← SOURCE: Next.js dashboard
├── mcp_server/                     ← SOURCE: MCP tool layer
└── ceo_assistant/                  ← SOURCE: Report generator
```

---

## Quick Reference — Trigger to Completion

| Trigger | First Action | Approval? | Notification |
|---------|-------------|-----------|--------------|
| Unread important Gmail | Gmail Watcher (15 min poll) | ✅ Yes | Email reply + WhatsApp |
| WhatsApp message | Webhook (instant) | ⚡ Depends on type | WhatsApp reply |
| LinkedIn mention | Social Watcher (15 min) | ✅ Yes | LinkedIn reply |
| Twitter mention | Social Watcher (15 min) | ✅ Yes | Twitter reply |
| GitHub PR/Issue | Webhook (instant) | ❌ No | WhatsApp summary |
| Frontend manual task | Instant | ⚡ Depends on type | WhatsApp summary |
| CEO report | Scheduler (18:00 UTC) | ❌ No | Email to CEO |

---

*Generated: 2026-02-28 | FTE v1.0 | Claude-powered autonomous task execution*
