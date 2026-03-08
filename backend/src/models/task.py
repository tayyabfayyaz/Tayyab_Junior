"""T013: Task Pydantic models — TaskCreate, TaskResponse, TaskListResponse."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TaskType(str, Enum):
    EMAIL_REPLY = "email_reply"
    EMAIL_DRAFT = "email_draft"
    SOCIAL_POST = "social_post"
    SOCIAL_REPLY = "social_reply"
    WHATSAPP_REPLY = "whatsapp_reply"
    CODING_TASK = "coding_task"
    SPEC_GENERATION = "spec_generation"
    GENERAL = "general"


class TaskPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskSource(str, Enum):
    GMAIL = "gmail"
    WHATSAPP = "whatsapp"
    LINKEDIN = "linkedin"
    TWITTER = "twitter"
    GITHUB = "github"
    FRONTEND = "frontend"
    SCHEDULER = "scheduler"


class TaskStatus(str, Enum):
    AWAITING_APPROVAL = "awaiting_approval"
    NEED_ACTION = "need_action"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


class TaskCreate(BaseModel):
    type: TaskType = TaskType.GENERAL
    priority: TaskPriority = TaskPriority.MEDIUM
    source: TaskSource = TaskSource.FRONTEND
    instruction: str = Field(..., min_length=1)
    context: str = Field(default="")
    constraints: Optional[str] = None
    expected_output: Optional[str] = None
    source_ref: Optional[str] = None


class TaskResponse(BaseModel):
    task_id: str
    type: TaskType
    priority: TaskPriority
    source: TaskSource
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    retry_count: int = 0
    source_ref: Optional[str] = None
    context: str = ""
    instruction: str = ""
    constraints: Optional[str] = None
    expected_output: Optional[str] = None
    result: Optional[str] = None
    error: Optional[str] = None
    instruction_preview: Optional[str] = None


class TaskListResponse(BaseModel):
    tasks: list[TaskResponse]
    total: int
    limit: int
    offset: int


class TaskRetryResponse(BaseModel):
    task_id: str
    status: TaskStatus
    retry_count: int


class TaskApprovalResponse(BaseModel):
    task_id: str
    status: TaskStatus


class TaskCreateResponse(BaseModel):
    task_id: str
    status: TaskStatus
    created_at: datetime
