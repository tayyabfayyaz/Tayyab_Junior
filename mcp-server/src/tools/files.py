"""T019-T020: MCP file_read and file_write tools."""

import time
from pathlib import Path

from mcp_server.src.logger import MCPLogger

logger = MCPLogger()


def file_read(path: str, task_id: str = "unknown") -> dict:
    """Read a file and return its content."""
    start = time.time()
    try:
        file_path = Path(path)
        if not file_path.exists():
            result = {"content": "", "exists": False}
            status = "success"
        else:
            content = file_path.read_text(encoding="utf-8")
            result = {"content": content, "exists": True}
            status = "success"
    except Exception as e:
        result = {"error": str(e)}
        status = "error"

    duration_ms = int((time.time() - start) * 1000)
    logger.log_invocation(task_id, "file_read", {"path": path}, result, status, duration_ms)
    return result


def file_write(path: str, content: str, mode: str = "write", task_id: str = "unknown") -> dict:
    """Write content to a file."""
    start = time.time()
    try:
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        if mode == "append":
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(content)
        else:
            file_path.write_text(content, encoding="utf-8")
        result = {"status": "written", "bytes": len(content.encode("utf-8"))}
        status = "success"
    except Exception as e:
        result = {"error": str(e)}
        status = "error"

    duration_ms = int((time.time() - start) * 1000)
    logger.log_invocation(task_id, "file_write", {"path": path, "mode": mode}, result, status, duration_ms)
    return result
