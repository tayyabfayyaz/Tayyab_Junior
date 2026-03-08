"""T029: Task CRUD router — list, get, create, retry endpoints."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Request

from backend.src.models.task import (
    TaskApprovalResponse,
    TaskCreate,
    TaskCreateResponse,
    TaskListResponse,
    TaskPriority,
    TaskResponse,
    TaskRetryResponse,
    TaskSource,
    TaskStatus,
    TaskType,
)
from backend.src.services.task_writer import write_task_file

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    request: Request,
    status: Optional[TaskStatus] = None,
    type: Optional[TaskType] = None,
    priority: Optional[TaskPriority] = None,
    source: Optional[TaskSource] = None,
    limit: int = 50,
    offset: int = 0,
    sort: str = "created_at:desc",
):
    engine = request.app.state.task_engine
    tasks, total = engine.list_tasks(
        status=status,
        task_type=type,
        priority=priority,
        source=source,
        limit=min(limit, 100),
        offset=offset,
        sort=sort,
    )
    return TaskListResponse(tasks=tasks, total=total, limit=limit, offset=offset)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(request: Request, task_id: str):
    engine = request.app.state.task_engine
    task = engine.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/manual", response_model=TaskCreateResponse, status_code=201)
async def create_manual_task(request: Request, task_data: TaskCreate):
    from pathlib import Path

    engine = request.app.state.task_engine
    task_data.source = TaskSource.FRONTEND
    # Manual tasks created by the user are already intentional — skip approval queue
    task_id, file_path = write_task_file(task_data, engine.task_dir, auto_approve=True)
    engine._log_transition(task_id, "created", "need_action", actor="frontend")

    task = engine.get_task(task_id)
    if not task:
        raise HTTPException(status_code=500, detail="Failed to create task")
    return TaskCreateResponse(task_id=task.task_id, status=task.status, created_at=task.created_at)


@router.post("/{task_id}/approve", response_model=TaskApprovalResponse)
async def approve_task(request: Request, task_id: str):
    engine = request.app.state.task_engine
    task = engine.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != TaskStatus.AWAITING_APPROVAL:
        raise HTTPException(status_code=400, detail="Task is not awaiting approval")
    engine.move_task(task_id, TaskStatus.NEED_ACTION, actor="user", detail="Approved by human")
    return TaskApprovalResponse(task_id=task_id, status=TaskStatus.NEED_ACTION)


@router.post("/{task_id}/reject", response_model=TaskApprovalResponse)
async def reject_task(request: Request, task_id: str):
    engine = request.app.state.task_engine
    task = engine.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != TaskStatus.AWAITING_APPROVAL:
        raise HTTPException(status_code=400, detail="Task is not awaiting approval")
    engine.move_task(task_id, TaskStatus.FAILED, actor="user", detail="Rejected by human")
    return TaskApprovalResponse(task_id=task_id, status=TaskStatus.FAILED)


@router.post("/{task_id}/retry", response_model=TaskRetryResponse)
async def retry_task(request: Request, task_id: str):
    engine = request.app.state.task_engine
    task = engine.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != TaskStatus.FAILED:
        raise HTTPException(status_code=400, detail="Task is not in failed state")

    from backend.src.config import settings

    if task.retry_count >= settings.executor_max_retries:
        raise HTTPException(status_code=400, detail="Max retries exceeded")

    # Increment retry count in file
    from pathlib import Path
    import re

    file_path = engine.task_dir / "failed" / f"{task_id}.md"
    content = file_path.read_text(encoding="utf-8")
    new_count = task.retry_count + 1
    content = re.sub(r"retry_count:\s*\d+", f"retry_count: {new_count}", content)
    file_path.write_text(content, encoding="utf-8")

    engine.move_task(task_id, TaskStatus.NEED_ACTION, actor="user", detail=f"Retry #{new_count}")
    return TaskRetryResponse(task_id=task_id, status=TaskStatus.NEED_ACTION, retry_count=new_count)
