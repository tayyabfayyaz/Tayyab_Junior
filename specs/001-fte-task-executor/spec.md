# Feature Specification: FTE – Fully Task Executor

**Feature Branch**: `001-fte-task-executor`
**Created**: 2026-02-13
**Status**: Draft
**Input**: User description: "Autonomous AI assistant system that monitors Email, WhatsApp, Social Media, GitHub, converts events into structured task files, and executes them via Claude Code through MCP tools"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Manual Task Creation & Execution (Priority: P1)

As the system owner, I want to create a task manually through the dashboard, have the AI assistant execute it autonomously, and see the result — so that I can verify the core execution loop works and delegate ad-hoc tasks to the AI.

**Why this priority**: This is the foundation of the entire system. Without a working task lifecycle (create → execute → complete), no other feature has value. This proves the core loop: task file creation, executor pickup, AI reasoning, tool execution, and result delivery.

**Independent Test**: Create a task via the dashboard saying "Summarize the key points of this document" with context text. Verify the task appears in the pending queue, the executor picks it up, processes it, and the result is visible in the completed tasks view.

**Acceptance Scenarios**:

1. **Given** the dashboard is open, **When** the user fills in the task creation form with an instruction and context, **Then** a new task appears in the "Pending" queue within 5 seconds.
2. **Given** a task exists in the pending queue, **When** the executor processes it, **Then** the task moves to "Processing" status and the dashboard reflects this change.
3. **Given** a task is being processed, **When** the AI completes execution successfully, **Then** the task moves to "Completed" with the result visible in the task detail view.
4. **Given** a task is being processed, **When** the AI encounters an unrecoverable error, **Then** the task moves to "Failed" with the error description preserved.
5. **Given** a failed task, **When** the user clicks "Retry", **Then** the task is re-queued for execution with an incremented retry counter.

---

### User Story 2 - WhatsApp Command Execution (Priority: P2)

As the system owner, I want to send a natural language command via WhatsApp (e.g., "Reply to Ali about the pricing proposal") and have the AI assistant execute the task and notify me on completion — so that I can delegate tasks from my phone without opening the dashboard.

**Why this priority**: WhatsApp is the primary mobile command interface. It enables the owner to delegate tasks from anywhere, anytime, making the system a true personal assistant rather than a dashboard-only tool.

**Independent Test**: Send a WhatsApp message "Draft a summary of today's meetings". Verify a task is created, the AI generates the summary, and a WhatsApp notification confirms completion with a preview of the result.

**Acceptance Scenarios**:

1. **Given** the WhatsApp integration is active, **When** the owner sends a message, **Then** the system creates a structured task within 10 seconds.
2. **Given** a WhatsApp-originated task, **When** the message contains a clear instruction (e.g., "Reply to Ali about pricing"), **Then** the system correctly identifies the task type, priority, and target.
3. **Given** a WhatsApp-originated task has been completed, **When** the result is ready, **Then** the system sends a WhatsApp notification to the owner with a completion summary.
4. **Given** a WhatsApp-originated task fails, **When** retries are exhausted, **Then** the system sends a WhatsApp notification explaining the failure.

---

### User Story 3 - Email Monitoring & Auto-Response (Priority: P3)

As the system owner, I want the AI to monitor my email inbox, detect messages that require a response, draft professional replies, and send them on my behalf — so that routine client emails are handled without my manual intervention.

**Why this priority**: Email is the highest-volume communication channel for professionals. Automating routine email responses delivers significant daily time savings and ensures prompt client communication.

**Independent Test**: Send a test email to the monitored inbox asking about service pricing. Verify the system detects it, classifies it as action-required, drafts a professional reply using stored knowledge, and sends it. Confirm the task record shows the full lifecycle.

**Acceptance Scenarios**:

1. **Given** a new email arrives in the monitored inbox, **When** the email watcher detects it, **Then** the system evaluates whether a response is required within 2 minutes.
2. **Given** an email classified as action-required, **When** the task is created, **Then** the task includes the sender, subject, body, and thread context.
3. **Given** an email response task, **When** the AI drafts a reply, **Then** the reply matches the owner's preferred writing tone and references relevant stored knowledge (client profiles, pricing info).
4. **Given** a drafted email reply, **When** execution completes, **Then** the reply is sent to the original sender via the owner's email account and the task is marked completed.
5. **Given** an email classified as informational (newsletters, notifications), **When** the watcher evaluates it, **Then** no task is created and the event is logged as "no action required".

---

### User Story 4 - Social Media Management (Priority: P4)

As the system owner, I want the AI to post scheduled content on LinkedIn and Twitter, and respond to comments and mentions — so that my social media presence stays active without daily manual effort.

**Why this priority**: Social media presence is important but less time-sensitive than email or WhatsApp. It can operate on scheduled intervals (hourly/daily) rather than real-time.

**Independent Test**: Schedule a LinkedIn post for a specific time with content guidelines. Verify the system generates the post content, publishes it at the scheduled time, and logs the published URL. Also verify that when a comment appears on an existing post, the system generates and publishes an appropriate reply.

**Acceptance Scenarios**:

1. **Given** a scheduled post time arrives, **When** the scheduler creates a posting task, **Then** the AI generates platform-appropriate content and publishes it via the owner's account.
2. **Given** a new comment on the owner's social media post, **When** the social watcher detects it, **Then** a response task is created with the comment context.
3. **Given** a social media reply task, **When** the AI generates a response, **Then** the response is contextually relevant, professionally toned, and published as a reply to the original comment.
4. **Given** a published social media action, **When** execution completes, **Then** the task record includes the published content URL and platform confirmation.

---

### User Story 5 - Task Dashboard & Visibility (Priority: P5)

As the system owner, I want a web dashboard that displays all tasks across all states (pending, processing, completed, failed) with filtering, search, and real-time updates — so that I have full visibility and control over what my AI assistant is doing.

**Why this priority**: Transparency is a core principle. The dashboard provides oversight, debugging capability, and the ability to intervene (retry, cancel) when needed. It supports all other stories by providing the monitoring interface.

**Independent Test**: Open the dashboard while tasks are being processed. Verify all task states are visible, filters work correctly, task details show full context and results, and status changes appear within seconds.

**Acceptance Scenarios**:

1. **Given** the dashboard is loaded, **When** tasks exist in various states, **Then** the dashboard displays task counts per status and a sortable task list.
2. **Given** a task changes status (e.g., pending → processing), **When** the dashboard is open, **Then** the status update appears within 5 seconds without page refresh.
3. **Given** the task list, **When** the user applies filters (by status, type, source, priority), **Then** only matching tasks are displayed.
4. **Given** a specific task, **When** the user clicks on it, **Then** the full task details are displayed including context, instruction, constraints, result (if completed), and error (if failed).

---

### Edge Cases

- What happens when the executor encounters a task with malformed or missing required fields? The system MUST reject the task, move it to failed with a validation error, and log the issue.
- What happens when multiple tasks arrive simultaneously from different watchers? The system MUST queue them in order of arrival and process them sequentially without data loss.
- What happens when an external service (Gmail, WhatsApp API, LinkedIn) is temporarily unavailable? The system MUST mark affected tasks as failed with a service-unavailable error and respect retry policies.
- What happens when the AI generates a response that the owner has not approved for a high-risk action (e.g., sending a financial proposal)? The system MUST hold the task and request explicit approval before executing the action.
- What happens when the memory layer contains outdated information (e.g., old pricing)? The AI MUST use the most recently modified memory documents and flag potential staleness based on document age.
- What happens when a WhatsApp message is ambiguous or cannot be parsed into a task? The system MUST reply asking for clarification rather than creating a malformed task.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST represent every unit of work as a structured task file with unique ID, type, priority, source, context, instruction, and expected output.
- **FR-002**: System MUST manage task lifecycle through four distinct states: pending (need_action), processing, completed (done), and failed.
- **FR-003**: System MUST provide a web dashboard for viewing all tasks across all lifecycle states with filtering by status, type, source, and priority.
- **FR-004**: System MUST allow manual task creation through the dashboard with required fields: instruction, context, type, and priority.
- **FR-005**: System MUST accept incoming WhatsApp messages and convert natural language commands into structured task files.
- **FR-006**: System MUST monitor an email inbox and automatically classify incoming emails as action-required or informational.
- **FR-007**: System MUST draft and send email replies on behalf of the owner when an email is classified as action-required.
- **FR-008**: System MUST monitor social media platforms for comments and mentions and create response tasks.
- **FR-009**: System MUST generate and publish social media posts on a configurable schedule.
- **FR-010**: System MUST execute all external actions (sending emails, posting to social media, sending WhatsApp messages) exclusively through a tool isolation layer — never directly.
- **FR-011**: System MUST load relevant context from a persistent knowledge store (user preferences, client profiles, writing tone) before executing any task.
- **FR-012**: System MUST log every task state transition with a timestamp, source, and actor.
- **FR-013**: System MUST log every tool invocation with inputs, outputs, status, and timing.
- **FR-014**: System MUST send a completion or failure notification to the owner via WhatsApp after each task originating from WhatsApp.
- **FR-015**: System MUST support task retry for failed tasks with a configurable maximum retry count (default: 3).
- **FR-016**: System MUST require explicit owner approval before executing high-risk actions (financial proposals, account modifications, bulk operations).
- **FR-017**: System MUST authenticate dashboard access and reject unauthorized requests.
- **FR-018**: System MUST verify the authenticity of incoming webhooks (WhatsApp, email, GitHub) using signature verification.
- **FR-019**: System MUST never store credentials or API tokens in code; all secrets MUST be managed through environment configuration.
- **FR-020**: System MUST apply rate limiting to all webhook and API endpoints.
- **FR-021**: System MUST provide a health check endpoint reporting the status of all system components (executor, watchers, tool layer, task directories).
- **FR-022**: System MUST run as independently deployable, containerized services.

### Key Entities

- **Task**: The fundamental unit of work. Contains a unique ID, type (email reply, social post, WhatsApp reply, coding task, general), priority (critical, high, medium, low), source (which platform originated it), context, instruction, constraints, expected output, and result. Lifecycle state is determined by which directory the task file resides in.
- **Watcher Event**: A raw event captured from an external platform (email, WhatsApp, social media, GitHub). Contains the original payload, detection timestamp, and whether it warrants a task. Related to at most one Task.
- **Tool Invocation**: A record of an external action performed by the tool layer on behalf of a task. Contains the tool name, input parameters, output, status, and timing. Related to exactly one Task.
- **Task Log**: An append-only record of every task state transition. Contains timestamp, task ID, from-state, to-state, and actor. Related to exactly one Task.
- **Memory Document**: A knowledge document in the persistent memory store. Organized by category (preferences, clients, tone, knowledge, logs). Read by the executor before task execution to provide context.
- **User**: The system owner. Single-user system for MVP. Contains profile information, connected account credentials (encrypted), and notification preferences.

### Assumptions

- The system serves a single owner (not multi-tenant) for the initial version.
- The owner has active accounts on the integrated platforms (Gmail, WhatsApp Business, LinkedIn, Twitter/X, GitHub).
- Task volume is moderate (~50-100 tasks per day) and sequential processing is acceptable.
- The owner's preferred writing tone and client knowledge will be pre-populated in the memory store before first use.
- WhatsApp Business API access has been approved by Meta.
- Email monitoring is limited to a single Gmail account.
- Social media posting requires pre-existing connected accounts with appropriate API permissions.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Tasks created manually via the dashboard are picked up and execution begins within 10 seconds.
- **SC-002**: WhatsApp commands result in a completed task with notification sent back to the owner within 2 minutes for simple tasks (text generation, replies).
- **SC-003**: 95% of incoming emails are correctly classified as action-required or informational.
- **SC-004**: Email responses drafted by the system match the owner's preferred tone as validated by the owner in 90% of cases (measured over first 30 days).
- **SC-005**: Social media posts are published within 1 minute of their scheduled time.
- **SC-006**: Dashboard reflects task status changes within 5 seconds of occurrence.
- **SC-007**: System maintains a 95% task completion rate (tasks that reach "completed" vs. total tasks created, excluding permanent failures from invalid input).
- **SC-008**: Zero external actions are executed without a corresponding tool invocation log entry (100% auditability).
- **SC-009**: System recovers from individual service failures (watcher crash, executor restart) within 60 seconds without losing pending tasks.
- **SC-010**: Owner spends less than 15 minutes per day reviewing and overriding AI assistant actions (measured over first 30 days), down from 2+ hours of manual task execution.
