"""T028/T066: Health check, stats, and SSE endpoints."""

import asyncio
import json

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

router = APIRouter(tags=["system"])


@router.get("/health")
async def health_check(request: Request):
    engine = request.app.state.task_engine
    counts = engine.count_by_status()
    gmail_watcher = getattr(request.app.state, "gmail_watcher", None)
    email_status = "active" if (gmail_watcher and gmail_watcher._running) else "inactive"
    social_watcher = getattr(request.app.state, "social_watcher", None)
    social_status = "active" if (social_watcher and social_watcher._running) else "inactive"
    return {
        "status": "healthy",
        "version": "1.0.0",
        "services": {
            "executor": "running",
            "watchers": {
                "email": email_status,
                "whatsapp": "inactive",
                "social": social_status,
                "github": "inactive",
            },
            "mcp_server": "connected",
            "task_dirs": counts,
        },
    }


@router.get("/stats")
async def task_stats(request: Request, period: str = "all"):
    engine = request.app.state.task_engine
    by_status = engine.count_by_status()
    by_type = engine.count_by_type()
    total = sum(by_status.values())
    return {
        "period": period,
        "total_tasks": total,
        "by_status": by_status,
        "by_type": by_type,
        "avg_execution_time_ms": 0,
    }


@router.get("/tasks/stream")
async def task_stream(request: Request):
    """T066: SSE endpoint — push task status changes to connected clients."""

    async def event_generator():
        engine = request.app.state.task_engine
        last_counts = engine.count_by_status()

        while True:
            await asyncio.sleep(2)

            # Check if client disconnected
            if await request.is_disconnected():
                break

            current_counts = engine.count_by_status()

            if current_counts != last_counts:
                # Task counts changed — emit event with updated data
                tasks, total = engine.list_tasks(limit=10, sort="updated_at:desc")
                event_data = {
                    "counts": current_counts,
                    "recent_tasks": [
                        {
                            "task_id": t.task_id,
                            "status": t.status.value,
                            "type": t.type.value,
                            "updated_at": t.updated_at.isoformat(),
                        }
                        for t in tasks
                    ],
                }
                yield f"data: {json.dumps(event_data)}\n\n"
                last_counts = current_counts

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
