"""T023: Executor configuration — polling interval, directories, API keys from env vars."""

import os
from dotenv import load_dotenv

load_dotenv()


class ExecutorConfig:
    poll_interval: int = int(os.getenv("EXECUTOR_POLL_INTERVAL_SECONDS", "5"))
    task_dir: str = os.getenv("TASK_DIR", "./tasks")
    memory_dir: str = os.getenv("MEMORY_DIR", "./memory")
    log_dir: str = os.getenv("LOG_DIR", "./logs")
    mcp_server_url: str = os.getenv("MCP_SERVER_URL", "http://mcp-server:8001")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    max_retries: int = int(os.getenv("EXECUTOR_MAX_RETRIES", "3"))


config = ExecutorConfig()
