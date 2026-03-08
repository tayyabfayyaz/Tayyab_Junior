"""Financial Assistant API — transactions, business summary, and finance chat."""

import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(prefix="/finance", tags=["finance"])


# ── Pydantic models ──────────────────────────────────────────────────────────

class Transaction(BaseModel):
    id: str
    date: str
    description: str
    amount: float
    currency: str = "PKR"
    type: str  # "credit" | "debit"
    source: str  # "email" | "file"
    bank: Optional[str] = None
    raw_ref: Optional[str] = None


class TransactionsResponse(BaseModel):
    transactions: list[Transaction]
    total: int
    last_synced: Optional[str] = None


class SyncResponse(BaseModel):
    synced: int
    total: int
    errors: list[str]


class BusinessSummary(BaseModel):
    summary: str
    generated_at: str
    transaction_count: int
    total_credits: float
    total_debits: float
    currency: str = "PKR"


class ChatMessage(BaseModel):
    role: str    # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


class ChatResponse(BaseModel):
    reply: str
    model: str = "gemini"


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_finance_files_dir() -> str:
    return os.getenv("FINANCE_FILES_DIR", "./finance_files")


def _call_gemini(prompt: str) -> str:
    from google import genai
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY", ""))
    response = client.models.generate_content(
        model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        contents=prompt,
    )
    return response.text.strip()


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/transactions", response_model=TransactionsResponse)
async def get_transactions(request: Request):
    """Return all stored transactions."""
    from backend.src.services.finance_parser import load_transactions
    store = load_transactions()
    txns = [Transaction(**t) for t in store.get("transactions", [])]
    txns.sort(key=lambda x: x.date, reverse=True)
    return TransactionsResponse(
        transactions=txns,
        total=len(txns),
        last_synced=store.get("last_synced"),
    )


@router.post("/transactions/sync", response_model=SyncResponse)
async def sync_transactions(request: Request):
    """Parse banking emails + scan system files for new transactions."""
    from backend.src.services.finance_parser import (
        parse_banking_emails, scan_system_files, load_transactions,
    )

    errors: list[str] = []
    total_synced = 0

    # Parse banking emails
    try:
        synced_email, email_errors = parse_banking_emails()
        total_synced += synced_email
        errors.extend(email_errors)
    except Exception as e:
        errors.append(f"Email sync failed: {e}")

    # Scan system files
    try:
        synced_files, file_errors = scan_system_files(_get_finance_files_dir())
        total_synced += synced_files
        errors.extend(file_errors)
    except Exception as e:
        errors.append(f"File scan failed: {e}")

    store = load_transactions()
    return SyncResponse(
        synced=total_synced,
        total=len(store.get("transactions", [])),
        errors=errors,
    )


@router.get("/business-summary", response_model=BusinessSummary)
async def get_business_summary(request: Request):
    """Return stored business summary, or generate one if it doesn't exist."""
    from backend.src.services.finance_parser import load_summary, generate_business_summary

    existing = load_summary()
    if existing:
        return BusinessSummary(**existing)

    # Auto-generate on first request
    engine = request.app.state.task_engine
    try:
        result = generate_business_summary(task_dir=engine.task_dir)
        return BusinessSummary(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summary generation failed: {e}")


@router.post("/business-summary/refresh", response_model=BusinessSummary)
async def refresh_business_summary(request: Request):
    """Force regenerate business summary using Gemini."""
    from backend.src.services.finance_parser import generate_business_summary

    engine = request.app.state.task_engine
    try:
        result = generate_business_summary(task_dir=engine.task_dir)
        return BusinessSummary(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summary generation failed: {e}")


@router.post("/chat", response_model=ChatResponse)
async def finance_chat(request: Request, body: ChatRequest):
    """Stateless finance chat — frontend sends full conversation history."""
    from backend.src.services.finance_parser import build_chat_context

    if not body.messages:
        raise HTTPException(status_code=400, detail="messages cannot be empty")

    context = build_chat_context()

    # Build conversation text
    convo_lines = []
    for msg in body.messages:
        label = "User" if msg.role == "user" else "Assistant"
        convo_lines.append(f"{label}: {msg.content}")

    convo_text = "\n".join(convo_lines)

    prompt = f"""You are a personal Finance Assistant for a business owner in Pakistan.
You have access to their real financial data. Be direct, specific, and helpful.
Use PKR for currency amounts. Suggest concrete next steps when relevant.

{context}

{convo_text}
Assistant:"""

    try:
        reply = _call_gemini(prompt)
        # Strip leading "Assistant:" if model echoed it
        reply = reply.removeprefix("Assistant:").strip()
        return ChatResponse(reply=reply, model="gemini")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI response failed: {e}")
