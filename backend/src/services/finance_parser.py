"""Financial data parser — banking emails, system files, Gemini-powered extraction."""

import csv
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

_MEMORY_DIR = Path(os.getenv("MEMORY_DIR", "./memory"))
_TRANSACTIONS_FILE = _MEMORY_DIR / "finance_transactions.json"
_SUMMARY_FILE = _MEMORY_DIR / "finance_summary.json"

_BANK_DOMAINS = [
    "mcb.com.pk", "hbl.com", "meezanbank.com", "ubldigital.com",
    "alfalabank.com", "habibbank.com", "bankislami.com.pk",
    "js.bank", "askari.com.pk", "standardchartered.com.pk",
    "jazz.com.pk", "easypaisa.com", "jazz-cash.com",
]

_BANK_KEYWORDS = ["bank", "transaction", "credit", "debit", "payment", "statement"]


# ── Store helpers ────────────────────────────────────────────────────────────

def load_transactions() -> dict:
    """Load stored transactions from memory."""
    if _TRANSACTIONS_FILE.exists():
        try:
            return json.loads(_TRANSACTIONS_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {"transactions": [], "last_synced": None}


def save_transactions(store: dict):
    _MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    _TRANSACTIONS_FILE.write_text(json.dumps(store, indent=2), encoding="utf-8")


def load_summary() -> Optional[dict]:
    if _SUMMARY_FILE.exists():
        try:
            return json.loads(_SUMMARY_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return None


def save_summary(summary: dict):
    _MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    _SUMMARY_FILE.write_text(json.dumps(summary, indent=2), encoding="utf-8")


# ── Gemini helper ────────────────────────────────────────────────────────────

def _call_gemini(prompt: str) -> str:
    from google import genai
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY", ""))
    response = client.models.generate_content(
        model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        contents=prompt,
    )
    return response.text.strip()


def _strip_code_fences(text: str) -> str:
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _make_txn_id(date: str, description: str, amount: float, source: str) -> str:
    raw = f"{date}|{description}|{amount}|{source}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


# ── Transaction parsing from emails ─────────────────────────────────────────

def _is_banking_email(from_addr: str, subject: str) -> bool:
    from_lower = from_addr.lower()
    subject_lower = subject.lower()
    if any(domain in from_lower for domain in _BANK_DOMAINS):
        return True
    if any(kw in from_lower for kw in ["bank", "noreply@", "alerts@"]):
        if any(kw in subject_lower for kw in _BANK_KEYWORDS):
            return True
    return False


def _extract_bank_name(from_addr: str) -> Optional[str]:
    bank_map = {
        "mcb": "MCB", "hbl": "HBL", "meezan": "Meezan", "ubl": "UBL",
        "alfalah": "Bank Alfalah", "habib": "Habib Bank", "bankislami": "BankIslami",
        "js.bank": "JS Bank", "askari": "Askari Bank", "easypaisa": "EasyPaisa",
        "jazzcash": "JazzCash", "standardchartered": "Standard Chartered",
    }
    lower = from_addr.lower()
    for key, name in bank_map.items():
        if key in lower:
            return name
    return None


def _parse_email_transactions(email_body: str, from_addr: str, subject: str) -> list[dict]:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    bank_name = _extract_bank_name(from_addr)

    prompt = f"""Extract all bank transactions from the email text below.

Return ONLY a valid JSON array — no markdown, no explanation, no code fences.
Each object must have exactly these keys:
  date (YYYY-MM-DD string), description (string), amount (positive float),
  currency ("PKR" or "USD"), type ("credit" or "debit"), bank (bank name string or null)

Rules:
- Amounts: "Rs. 25,000" / "PKR 25,000" / "USD 100.00" → normalize to positive float
- "credited" / "deposited" / "received" → type = "credit"
- "debited" / "charged" / "withdrawn" / "paid" → type = "debit"
- If no date found, use: {today}
- If no transactions found, return empty array: []

Email subject: {subject}
Email text:
---
{email_body[:3000]}
---"""

    try:
        raw = _call_gemini(prompt)
        raw = _strip_code_fences(raw)
        items = json.loads(raw)
        if not isinstance(items, list):
            return []
        results = []
        for item in items:
            if not isinstance(item, dict):
                continue
            results.append({
                "id": _make_txn_id(
                    item.get("date", today),
                    item.get("description", ""),
                    float(item.get("amount", 0)),
                    "email",
                ),
                "date": item.get("date", today),
                "description": str(item.get("description", "")).strip(),
                "amount": float(item.get("amount", 0)),
                "currency": item.get("currency", "PKR"),
                "type": item.get("type", "debit"),
                "source": "email",
                "bank": item.get("bank") or bank_name,
                "raw_ref": subject[:100],
            })
        return results
    except Exception as e:
        print(f"[finance_parser] Email parse error: {e}")
        return []


def parse_banking_emails() -> tuple[int, list[str]]:
    """Fetch banking emails from Gmail and extract transactions. Returns (new_count, errors)."""
    errors = []
    new_transactions = []

    try:
        from watchers.src.gmail_service import list_unread_emails, get_email, mark_as_read
        emails = list_unread_emails(max_results=50)
    except Exception as e:
        return 0, [f"Gmail unavailable: {e}"]

    store = load_transactions()
    existing_ids = {t["id"] for t in store["transactions"]}

    for stub in emails:
        try:
            email = get_email(stub["id"])
            if not _is_banking_email(email.get("from", ""), email.get("subject", "")):
                continue
            body = email.get("body", "") or email.get("snippet", "")
            if not body:
                continue
            txns = _parse_email_transactions(body, email["from"], email["subject"])
            for txn in txns:
                if txn["id"] not in existing_ids:
                    new_transactions.append(txn)
                    existing_ids.add(txn["id"])
        except Exception as e:
            errors.append(f"Email {stub.get('id','?')}: {e}")

    store["transactions"].extend(new_transactions)
    store["last_synced"] = datetime.now(timezone.utc).isoformat()
    save_transactions(store)
    return len(new_transactions), errors


# ── Transaction parsing from system files ────────────────────────────────────

def _parse_csv_file(file_path: Path) -> list[dict]:
    """Parse a CSV file as transactions. Tries to detect columns automatically."""
    transactions = []
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    try:
        with open(file_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            headers = [h.lower().strip() for h in (reader.fieldnames or [])]

            date_col = next((h for h in headers if "date" in h), None)
            desc_col = next((h for h in headers if any(k in h for k in ["desc", "narr", "detail", "particular", "remark"])), None)
            amount_col = next((h for h in headers if any(k in h for k in ["amount", "amt", "value"])), None)
            credit_col = next((h for h in headers if "credit" in h), None)
            debit_col = next((h for h in headers if "debit" in h), None)

            for row in reader:
                try:
                    raw_lower = {k.lower().strip(): v for k, v in row.items()}
                    date = raw_lower.get(date_col, today) if date_col else today
                    description = raw_lower.get(desc_col, "File transaction") if desc_col else "File transaction"

                    # Determine amount and type
                    txn_type = "debit"
                    amount = 0.0
                    if credit_col and debit_col:
                        cr = raw_lower.get(credit_col, "").replace(",", "").strip()
                        db = raw_lower.get(debit_col, "").replace(",", "").strip()
                        if cr and cr not in ("0", "0.00", ""):
                            amount = abs(float(cr))
                            txn_type = "credit"
                        elif db and db not in ("0", "0.00", ""):
                            amount = abs(float(db))
                            txn_type = "debit"
                    elif amount_col:
                        raw_amt = raw_lower.get(amount_col, "0").replace(",", "").strip()
                        amount = abs(float(raw_amt))
                        txn_type = "credit" if amount > 0 else "debit"

                    if amount == 0:
                        continue

                    # Normalise date
                    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%d %b %Y"):
                        try:
                            date = datetime.strptime(date.strip(), fmt).strftime("%Y-%m-%d")
                            break
                        except ValueError:
                            pass

                    transactions.append({
                        "id": _make_txn_id(date, description, amount, f"file:{file_path.name}"),
                        "date": date,
                        "description": description.strip(),
                        "amount": amount,
                        "currency": "PKR",
                        "type": txn_type,
                        "source": "file",
                        "bank": None,
                        "raw_ref": file_path.name,
                    })
                except (ValueError, TypeError):
                    continue
    except Exception as e:
        print(f"[finance_parser] CSV parse error {file_path}: {e}")

    return transactions


def scan_system_files(folder: str) -> tuple[int, list[str]]:
    """Scan CSV (and optionally PDF) files in folder. Returns (new_count, errors)."""
    errors = []
    new_transactions = []
    folder_path = Path(folder)

    if not folder_path.exists():
        folder_path.mkdir(parents=True, exist_ok=True)
        return 0, []

    store = load_transactions()
    existing_ids = {t["id"] for t in store["transactions"]}

    for file_path in folder_path.iterdir():
        if file_path.suffix.lower() == ".csv":
            txns = _parse_csv_file(file_path)
            for txn in txns:
                if txn["id"] not in existing_ids:
                    new_transactions.append(txn)
                    existing_ids.add(txn["id"])
        elif file_path.suffix.lower() == ".pdf":
            try:
                import pdfplumber
                with pdfplumber.open(file_path) as pdf:
                    text = "\n".join(page.extract_text() or "" for page in pdf.pages)
                txns = _parse_email_transactions(text, "", file_path.name)
                for txn in txns:
                    txn["source"] = "file"
                    txn["raw_ref"] = file_path.name
                    if txn["id"] not in existing_ids:
                        new_transactions.append(txn)
                        existing_ids.add(txn["id"])
            except ImportError:
                pass  # pdfplumber not installed — silently skip PDFs
            except Exception as e:
                errors.append(f"PDF {file_path.name}: {e}")

    store["transactions"].extend(new_transactions)
    store["last_synced"] = datetime.now(timezone.utc).isoformat()
    save_transactions(store)
    return len(new_transactions), errors


# ── Business summary generation ──────────────────────────────────────────────

def generate_business_summary(task_dir: Optional[str] = None) -> dict:
    """Generate AI business health summary from transactions + task stats."""
    store = load_transactions()
    transactions = store.get("transactions", [])

    now = datetime.now(timezone.utc)
    cutoff_30d = (now - timedelta(days=30)).strftime("%Y-%m-%d")

    recent = [t for t in transactions if t.get("date", "") >= cutoff_30d]
    total_credits = sum(t["amount"] for t in transactions if t["type"] == "credit")
    total_debits = sum(t["amount"] for t in transactions if t["type"] == "debit")

    # Build transaction table for prompt
    last_20 = sorted(transactions, key=lambda x: x.get("date", ""), reverse=True)[:20]
    txn_lines = "\n".join(
        f"{t['date']} | {t['description'][:50]} | PKR {t['amount']:,.0f} | {t['type']}"
        for t in last_20
    ) or "No transactions recorded yet."

    # Task stats
    task_stats = "N/A"
    if task_dir:
        try:
            task_path = Path(task_dir)
            done = len(list((task_path / "done").glob("*.md"))) if (task_path / "done").exists() else 0
            failed = len(list((task_path / "failed").glob("*.md"))) if (task_path / "failed").exists() else 0
            task_stats = f"Completed tasks: {done}, Failed: {failed}"
        except Exception:
            pass

    prompt = f"""You are a business analyst for a solo entrepreneur in Pakistan. Write a concise 4-section Business Health Summary.

--- DATA ---
Total transactions on record: {len(transactions)}
All-time Credits: PKR {total_credits:,.0f}
All-time Debits: PKR {total_debits:,.0f}
Net Position: PKR {total_credits - total_debits:,.0f}

Last 20 transactions:
{txn_lines}

System task activity: {task_stats}
---

Write the summary with these 4 sections (use markdown bold for headers):
**1. Cash Flow Overview** — key numbers, net position
**2. Key Spending Patterns** — top 3 expense categories inferred from descriptions
**3. Revenue Signals** — notable income events or patterns
**4. Recommended Next Steps** — 2-3 specific actionable suggestions

Be direct, factual, and specific. Use PKR. Avoid filler phrases."""

    summary_text = _call_gemini(prompt)

    result = {
        "summary": summary_text,
        "generated_at": now.isoformat(),
        "transaction_count": len(transactions),
        "total_credits": total_credits,
        "total_debits": total_debits,
        "currency": "PKR",
    }
    save_summary(result)
    return result


# ── Finance chat context builder ─────────────────────────────────────────────

def build_chat_context() -> str:
    """Build a financial context string to prepend to chat prompts."""
    store = load_transactions()
    transactions = store.get("transactions", [])
    summary_data = load_summary()

    now = datetime.now(timezone.utc)
    cutoff_30d = (now - timedelta(days=30)).strftime("%Y-%m-%d")

    credits_30d = sum(t["amount"] for t in transactions if t["type"] == "credit" and t.get("date", "") >= cutoff_30d)
    debits_30d = sum(t["amount"] for t in transactions if t["type"] == "debit" and t.get("date", "") >= cutoff_30d)

    last_10 = sorted(transactions, key=lambda x: x.get("date", ""), reverse=True)[:10]
    txn_lines = "\n".join(
        f"  {t['date']} | {t['description'][:40]} | PKR {t['amount']:,.0f} | {t['type']}"
        for t in last_10
    ) or "  No transactions recorded yet."

    summary_snippet = ""
    if summary_data:
        summary_snippet = summary_data.get("summary", "")[:400]

    return f"""--- FINANCIAL CONTEXT (as of {now.strftime('%Y-%m-%d')}) ---
Total transactions on record: {len(transactions)}
Last 30 days: Credits PKR {credits_30d:,.0f} | Debits PKR {debits_30d:,.0f} | Net PKR {credits_30d - debits_30d:,.0f}
Recent transactions:
{txn_lines}
Business summary: {summary_snippet or 'Not generated yet — ask the user to refresh Business Details.'}
---"""
