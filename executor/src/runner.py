"""T026: Executor runner — parse task, load memory, invoke Claude SDK, collect result."""

import re
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml

from executor.src.config import config
from executor.src.memory_loader import load_memory


def _parse_task_file(file_path: Path) -> Optional[dict]:
    """Parse a task file and return its metadata and body sections."""
    try:
        raw = file_path.read_text(encoding="utf-8")
    except Exception:
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

    body = parts[2]

    def extract_section(heading: str) -> str:
        pattern = rf"##\s+{re.escape(heading)}\s*\n(.*?)(?=\n##\s|\Z)"
        match = re.search(pattern, body, re.DOTALL)
        return match.group(1).strip() if match else ""

    return {
        "meta": meta,
        "body": body,
        "context": extract_section("Context"),
        "instruction": extract_section("Instruction"),
        "constraints": extract_section("Constraints"),
        "expected_output": extract_section("Expected Output"),
    }


_SOCIAL_OUTPUT_INSTRUCTION = (
    "IMPORTANT — Output Format: Output ONLY the final post text, ready to publish. "
    "Do NOT include any preamble, explanation, or closing remarks (e.g. 'Here is a post...', "
    "'I hope this helps', etc.). "
    "Do NOT use markdown formatting (no **, ##, ---, bullet dashes). "
    "Use plain text with line breaks. Start directly with the post content."
)


def _build_prompt(task: dict, memory_context: str) -> str:
    """Build the prompt for Claude from task data and memory context."""
    parts = []

    task_type = task["meta"].get("type", "general")
    if task_type in ("social_post", "social_reply"):
        parts.append(f"## Output Format Instruction\n\n{_SOCIAL_OUTPUT_INSTRUCTION}")

    if memory_context:
        parts.append(f"## Relevant Context from Memory\n\n{memory_context}")

    parts.append(f"## Task Context\n\n{task['context']}")
    parts.append(f"## Instruction\n\n{task['instruction']}")

    if task["constraints"]:
        parts.append(f"## Constraints\n\n{task['constraints']}")

    if task["expected_output"]:
        parts.append(f"## Expected Output Format\n\n{task['expected_output']}")

    return "\n\n".join(parts)


def _append_result_to_file(file_path: Path, result: str):
    """Append a Result section to the task file."""
    content = file_path.read_text(encoding="utf-8")
    content += f"\n\n## Result\n{result}\n"
    now = datetime.now(timezone.utc).isoformat()
    content = re.sub(r"updated_at:\s*'[^']*'", f"updated_at: '{now}'", content)
    file_path.write_text(content, encoding="utf-8")


def _append_error_to_file(file_path: Path, error: str):
    """Append an Error section to the task file."""
    content = file_path.read_text(encoding="utf-8")
    content += f"\n\n## Error\n{error}\n"
    now = datetime.now(timezone.utc).isoformat()
    content = re.sub(r"updated_at:\s*'[^']*'", f"updated_at: '{now}'", content)
    file_path.write_text(content, encoding="utf-8")


def _invoke_gemini(prompt: str) -> str:
    """Call Google Gemini and return response text."""
    from google import genai

    client = genai.Client(api_key=config.gemini_api_key)
    response = client.models.generate_content(
        model=config.gemini_model,
        contents=prompt,
    )
    return response.text


def _invoke_anthropic(prompt: str) -> str:
    """Call Anthropic Claude and return response text."""
    import anthropic

    client = anthropic.Anthropic(api_key=config.anthropic_api_key)
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def _invoke_ai(prompt: str) -> str:
    """Invoke AI: Gemini first (free), fall back to Anthropic."""
    if config.gemini_api_key:
        return _invoke_gemini(prompt)
    if config.anthropic_api_key and not config.anthropic_api_key.startswith("sk-ant-xxx"):
        return _invoke_anthropic(prompt)
    raise RuntimeError(
        "No AI provider configured. Set GEMINI_API_KEY or ANTHROPIC_API_KEY in .env"
    )


async def run_task(file_path: Path) -> tuple[bool, str]:
    """Execute a task: parse, load memory, invoke Claude, return (success, result_or_error)."""
    task = _parse_task_file(file_path)
    if task is None:
        error = "Failed to parse task file"
        _append_error_to_file(file_path, error)
        return False, error

    task_type = task["meta"].get("type", "general")
    task_source = task["meta"].get("source", "frontend")

    memory_context = load_memory(config.memory_dir, task_type, task_source)
    prompt = _build_prompt(task, memory_context)

    from executor.src.notifications import send_task_notification

    try:
        result = _invoke_ai(prompt)
        _append_result_to_file(file_path, result)
    except Exception as e:
        error = f"AI generation failed — {type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        _append_error_to_file(file_path, error)
        send_task_notification(
            task_id=str(task["meta"].get("task_id", "")),
            task_source=task_source,
            source_ref=task["meta"].get("source_ref"),
            success=False,
            result_preview=error,
            task_type=task_type,
        )
        return False, error

    try:
        send_task_notification(
            task_id=str(task["meta"].get("task_id", "")),
            task_source=task_source,
            source_ref=task["meta"].get("source_ref"),
            success=True,
            result_preview=result,
            task_type=task_type,
        )
        return True, result
    except Exception as e:
        error = f"Action failed — {type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        _append_error_to_file(file_path, error)
        return False, error
