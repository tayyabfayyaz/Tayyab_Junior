# Complete System Documentation

**Version:** 1.0
**Author:** Muhammad Tayyab

---

## 1. Introduction

### 1.1 Project Overview

FTE (Fully Task Executor) is a personal AI assistant system designed to autonomously perform daily operational tasks on behalf of the user.

The system monitors multiple platforms (Email, WhatsApp, Social Media, GitHub), converts actionable events into structured task files, and executes them using Claude Code in autonomous mode.

FTE acts as:

- An AI Operations Manager
- A Personal Automation Engine
- A Spec-Driven Development Assistant
- A WhatsApp-commanded AI Worker

### 1.2 Problem Statement

Professionals spend significant time performing repetitive daily tasks such as:

- Reviewing and replying to emails
- Posting and replying on social media
- Responding to WhatsApp messages
- Managing coding and project specs

These tasks reduce focus on high-value thinking and strategy.

FTE solves this by:

- Automating repetitive digital operations through a structured AI execution pipeline.

---

## 2. Project Goals

### Primary Goals

- Automate daily digital workflows
- Enable WhatsApp-based AI task commands
- Use structured spec-driven execution
- Maintain task transparency via file system
- Provide memory persistence

### Secondary Goals

- Scalable microservice architecture
- Secure external API handling
- Future multi-agent upgrade support

---

## 3. User Stories

### 3.1 WhatsApp Command User Story

**As a user,**
I want to send a message on WhatsApp like:

> "Reply to Ali about the pricing proposal."

**So that**
My AI assistant executes the task automatically and informs me when it is complete.

**Acceptance Criteria:**

- [ ] WhatsApp message triggers task creation
- [ ] Task file is stored in /tasks/need_action
- [ ] Claude executes task
- [ ] Completion notification sent via WhatsApp

### 3.2 Email Automation User Story

**As a user,**
I want FTE to review my emails daily and respond to important ones professionally.

**So that**
I do not manually manage routine client emails.

**Acceptance Criteria:**

- [ ] Gmail watcher detects new email
- [ ] If response required, task file created
- [ ] Claude drafts response
- [ ] Email sent via MCP email tool
- [ ] Task moved to /done

### 3.3 Social Media Management User Story

**As a user,**
I want FTE to post daily content and respond to comments on LinkedIn and Twitter.

**So that**
My social presence remains active without manual work.

**Acceptance Criteria:**

- [ ] Social watcher detects comments or scheduled post
- [ ] Task generated
- [ ] Claude generates response/post
- [ ] MCP tool publishes content
- [ ] Completion logged

### 3.4 Coding & Spec-Driven Development User Story

**As a developer,**
I want to send a task like:

> "Create spec for Kafka-based notification system."

**So that**
Claude generates structured spec and development plan.

**Acceptance Criteria:**

- [ ] Task file created
- [ ] Claude produces structured documentation
- [ ] Output stored in /done
- [ ] Frontend displays result

### 3.5 Task Transparency User Story

**As a user,**
I want to see all tasks (pending, processing, completed, failed) in a dashboard.

**So that**
I have visibility and control over my AI assistant.

---

## 4. System Architecture Overview

FTE uses a modular microservice-style architecture.

### 4.1 High-Level Architecture Diagram

```
User (WhatsApp / Frontend)
        |
        v
Next.js Frontend
        |
        v
FastAPI Backend
        |
        v
Task Manager
        |
        v
Watchers
        |
        v
Task File System
        |
        v
Claude Executor
        |
        v
MCP Server
        |
        v
External APIs
        |
        v
Notification Service
```

---

## 5. Core Components

### 5.1 Frontend (Next.js)

**Purpose:**

- Task dashboard
- Task logs
- System status
- Manual task creation

**Features:**

- View /need_action
- View /done
- View /failed
- Real-time status

### 5.2 Backend (FastAPI)

**Responsibilities:**

- Receive webhooks (WhatsApp, Email)
- Create task files
- Serve task status API
- Handle authentication
- Connect to MCP server

**Endpoints:**

| Method | Path                | Description              |
|--------|---------------------|--------------------------|
| POST   | /whatsapp/webhook   | Receive WhatsApp events  |
| POST   | /email/webhook      | Receive email events     |
| GET    | /tasks              | List all tasks           |
| GET    | /tasks/{id}         | Get task by ID           |
| POST   | /task/manual        | Create task manually     |

### 5.3 Watcher System

Watchers continuously monitor platforms.

**Types:**

- Email Watcher
- WhatsApp Webhook
- Social Media Watcher
- GitHub Watcher
- Scheduler (cron-based)

If action required:
→ Create structured `.md` task file

### 5.4 Task File System (Core Design)

This is the execution backbone.

```
/tasks
   /need_action
   /processing
   /done
   /failed
```

**Task Lifecycle:**

1. Task Created
2. Stored in `/need_action`
3. Executor picks task
4. Moved to `/processing`
5. Executed
6. On success → `/done`
7. On error → `/failed`

This design ensures:

- Transparency
- Debugging capability
- Easy audit
- Simplicity

### 5.5 Claude Executor Engine

This is the AI brain.

**Responsibilities:**

- Read task file
- Parse instruction
- Load memory context
- Execute reasoning
- Call MCP tools
- Generate output
- Move file to correct directory

Runs in autonomous loop mode.

### 5.6 MCP Server (Tool Layer)

Claude never directly sends emails or posts content.

Instead:

```
Claude → MCP → External APIs
```

**MCP tools include:**

- Email sender
- Social media poster
- File editor
- Shell command runner

This increases:

- Security
- Control
- Auditability

### 5.7 Memory Layer (Obsidian Vault)

**Stores:**

- User preferences
- Client profiles
- Writing tone
- Project knowledge
- Logs

Claude loads relevant memory before execution.

---

## 6. Task File Structure Design

**Example:**

```markdown
# Task ID: 2026-02-12-001
Type: Email Reply
Priority: High
Source: Gmail

## Context
Client asked about enterprise pricing.

## Instruction
Draft a professional email reply explaining pricing.

## Constraints
Formal tone
Mention enterprise tier

## Expected Output
Email body text
```

---

## 7. Execution Flow Example

**Example:** User sends WhatsApp message:

> "Reply to Ali about proposal."

**Flow:**

1. WhatsApp webhook triggers
2. Backend creates task file
3. File saved in `/need_action`
4. Executor detects task
5. Moves to `/processing`
6. Claude reasons and generates reply
7. MCP sends email
8. Task moved to `/done`
9. WhatsApp sends "Task completed"

---

## 8. Security Architecture

**Security measures:**

- OAuth2 authentication
- Encrypted API tokens
- MCP tool isolation
- Execution logs
- Rate limiting
- Manual approval for high-risk actions

---

## 9. Non-Functional Requirements

**Performance:**

- Task execution under defined SLA
- Watcher polling optimized

**Scalability:**

- Microservice-ready
- Docker-ready
- Kubernetes-ready

**Reliability:**

- Error handling
- Retry mechanism
- Fail-safe task handling

**Auditability:**

- Every task logged
- No silent execution

---

## 10. Deployment Architecture

**Services:**

- Frontend Container
- Backend Container
- Executor Container
- Watchers Container
- MCP Container

**Managed via:**

- Docker Compose (MVP)
- Kubernetes (Future)

---

## 11. Future Enhancements

- Multi-agent architecture
- Priority queue system
- AI self-improvement
- Voice command integration
- Cloud distributed execution

---

## 12. Conclusion

FTE is not just an AI chatbot.

It is:

- A Personal AI Operating System
- A File-Based Task Execution Engine
- A WhatsApp-Controlled Automation Agent
- A Spec-Driven Development Assistant

If implemented properly, this system becomes:

**A Personal Autonomous Digital Workforce.**
