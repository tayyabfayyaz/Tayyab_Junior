"""T017/T030/T073: FastAPI app entry point — CORS, auth, rate limiting, routers, lifespan."""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.src.config import settings
from backend.src.services.task_engine import TaskEngine
from backend.src.api import tasks, system, webhooks, auth, reports, finance
from backend.src.middleware.rate_limit import RateLimitMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure reports directory exists
    from pathlib import Path
    Path(settings.reports_dir).mkdir(parents=True, exist_ok=True)

    app.state.task_engine = TaskEngine(
        task_dir=settings.task_dir,
        log_dir=settings.log_dir,
    )

    # Start Gmail watcher as background task if configured
    app.state.gmail_watcher = None
    gmail_task = None
    if settings.gmail_client_id:
        from watchers.src.gmail_watcher import GmailWatcher
        watcher = GmailWatcher(task_dir=settings.task_dir, log_dir=settings.log_dir)
        app.state.gmail_watcher = watcher
        gmail_task = asyncio.create_task(watcher.start())
        print("[lifespan] Gmail watcher started (poll every 15 min)")

    # Start Social (LinkedIn) watcher as background task if configured
    app.state.social_watcher = None
    social_task = None
    if settings.linkedin_client_id:
        from watchers.src.social_watcher import SocialWatcher
        social_watcher = SocialWatcher(task_dir=settings.task_dir, log_dir=settings.log_dir)
        app.state.social_watcher = social_watcher
        social_task = asyncio.create_task(social_watcher.start())
        print("[lifespan] LinkedIn/Social watcher started (poll every 15 min)")

    yield

    # Graceful shutdown
    if app.state.gmail_watcher:
        app.state.gmail_watcher.stop()
    if gmail_task:
        gmail_task.cancel()
        try:
            await gmail_task
        except asyncio.CancelledError:
            pass

    if app.state.social_watcher:
        app.state.social_watcher.stop()
    if social_task:
        social_task.cancel()
        try:
            await social_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="FTE – Fully Task Executor API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(RateLimitMiddleware, default_limit=100, window_seconds=60)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(tasks.router, prefix="/api/v1")
app.include_router(system.router, prefix="/api/v1")
app.include_router(webhooks.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")
app.include_router(finance.router, prefix="/api/v1")
