"""T022: MCP invocation logger — append-only JSONL logger for tool invocations."""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


class MCPLogger:
    def __init__(self, log_dir: str = "./logs"):
        self.log_path = Path(log_dir) / "mcp-invocations.jsonl"
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log_invocation(
        self,
        task_id: str,
        tool_name: str,
        input_params: dict,
        output: dict,
        status: str,
        duration_ms: int,
    ) -> str:
        invocation_id = str(uuid.uuid4())[:8]
        entry = {
            "invocation_id": invocation_id,
            "task_id": task_id,
            "tool_name": tool_name,
            "input_params": input_params,
            "output": output,
            "status": status,
            "duration_ms": duration_ms,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
        return invocation_id
