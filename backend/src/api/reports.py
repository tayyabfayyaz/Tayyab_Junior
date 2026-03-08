"""CEO Assistant — Reports API router."""

import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(prefix="/reports", tags=["reports"])


class ReportSummary(BaseModel):
    report_id: str
    generated_at: str
    title: str
    total_tasks: int
    completed: int
    failed: int


class ReportDetail(ReportSummary):
    content: str


class ReportGenerateResponse(BaseModel):
    report_id: str
    path: str


def _parse_report_file(file_path: Path) -> Optional[ReportSummary]:
    """Parse YAML frontmatter from a report markdown file into ReportSummary."""
    try:
        raw = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None

    parts = raw.split("---", 2)
    if len(parts) < 3:
        return None

    try:
        meta = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None

    if not isinstance(meta, dict):
        return None

    report_id = str(meta.get("report_id", file_path.stem))
    generated_at = str(meta.get("generated_at", ""))
    total = int(meta.get("total_tasks", 0))
    completed = int(meta.get("completed", 0))
    failed = int(meta.get("failed", 0))

    # Derive a human title from the report_id (YYYY-MM-DD)
    try:
        dt = datetime.strptime(report_id, "%Y-%m-%d")
        title = f"CEO Daily Report — {dt.strftime('%B %d, %Y')}"
    except ValueError:
        title = f"CEO Report — {report_id}"

    return ReportSummary(
        report_id=report_id,
        generated_at=generated_at,
        title=title,
        total_tasks=total,
        completed=completed,
        failed=failed,
    )


def _reports_dir(request: Request) -> Path:
    from backend.src.config import settings
    return Path(settings.reports_dir)


@router.get("", response_model=list[ReportSummary])
async def list_reports(request: Request):
    """List all CEO reports, newest first."""
    rdir = _reports_dir(request)
    if not rdir.exists():
        return []

    reports = []
    for f in sorted(rdir.glob("*.md"), reverse=True):
        summary = _parse_report_file(f)
        if summary:
            reports.append(summary)

    return reports


@router.get("/{report_id}", response_model=ReportDetail)
async def get_report(request: Request, report_id: str):
    """Return full content of a single report."""
    # Sanitize report_id to prevent path traversal
    if not re.match(r"^[\w\-]+$", report_id):
        raise HTTPException(status_code=400, detail="Invalid report ID")

    rdir = _reports_dir(request)
    file_path = rdir / f"{report_id}.md"

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Report not found")

    summary = _parse_report_file(file_path)
    if not summary:
        raise HTTPException(status_code=500, detail="Failed to parse report")

    content = file_path.read_text(encoding="utf-8")
    return ReportDetail(**summary.model_dump(), content=content)


@router.post("/generate", response_model=ReportGenerateResponse, status_code=201)
async def generate_report_now(request: Request):
    """Manually trigger report generation for today."""
    try:
        from ceo_assistant.src.report_generator import generate_report
        from backend.src.config import settings

        report_path = generate_report(
            reports_dir=settings.reports_dir,
            task_dir=settings.task_dir,
        )
        report_id = report_path.stem
        return ReportGenerateResponse(report_id=report_id, path=str(report_path))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {e}")
