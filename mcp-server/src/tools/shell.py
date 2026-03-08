"""T021: MCP shell_exec tool — execute subprocess commands with timeout."""

import subprocess
import time

from mcp_server.src.logger import MCPLogger

logger = MCPLogger()


def shell_exec(command: str, working_dir: str = ".", timeout_ms: int = 30000, task_id: str = "unknown") -> dict:
    """Execute a shell command and return stdout/stderr/exit_code."""
    start = time.time()
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=timeout_ms / 1000,
        )
        output = {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
        }
        status = "success"
    except subprocess.TimeoutExpired:
        output = {"stdout": "", "stderr": "Command timed out", "exit_code": -1}
        status = "error"
    except Exception as e:
        output = {"stdout": "", "stderr": str(e), "exit_code": -1}
        status = "error"

    duration_ms = int((time.time() - start) * 1000)
    logger.log_invocation(task_id, "shell_exec", {"command": command, "working_dir": working_dir}, output, status, duration_ms)
    return output
