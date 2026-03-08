"""T018: MCP server entry point — initialize MCP server with tool registry."""

import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

load_dotenv()

from mcp_server.src.tools.files import file_read, file_write
from mcp_server.src.tools.shell import shell_exec
from mcp_server.src.tools.email import email_send
from mcp_server.src.tools.social import social_post, social_reply


TOOLS = {
    "file_read": {
        "fn": file_read,
        "description": "Read a file and return its content",
        "params": {"path": "string"},
    },
    "file_write": {
        "fn": file_write,
        "description": "Write content to a file",
        "params": {"path": "string", "content": "string", "mode": "string"},
    },
    "shell_exec": {
        "fn": shell_exec,
        "description": "Execute a shell command",
        "params": {"command": "string", "working_dir": "string", "timeout_ms": "integer"},
    },
    "email_send": {
        "fn": email_send,
        "description": "Send an email via Gmail API",
        "params": {
            "to": "string",
            "subject": "string",
            "body": "string",
            "reply_to_message_id": "string",
            "thread_id": "string",
        },
    },
    "social_post": {
        "fn": social_post,
        "description": "Publish a post to LinkedIn or Twitter",
        "params": {"platform": "string", "content": "string", "media_urls": "list"},
    },
    "social_reply": {
        "fn": social_reply,
        "description": "Reply to a post or comment on LinkedIn or Twitter",
        "params": {"platform": "string", "reply_to_id": "string", "content": "string"},
    },
}


async def handle_request(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    """Handle incoming MCP tool invocation requests via TCP."""
    data = await reader.read(65536)
    if not data:
        writer.close()
        return

    try:
        request = json.loads(data.decode("utf-8"))
        tool_name = request.get("tool")
        params = request.get("params", {})
        task_id = request.get("task_id", "unknown")

        if tool_name not in TOOLS:
            response = {"error": f"Unknown tool: {tool_name}"}
        else:
            fn = TOOLS[tool_name]["fn"]
            params["task_id"] = task_id
            response = fn(**params)
    except Exception as e:
        response = {"error": str(e)}

    writer.write(json.dumps(response).encode("utf-8"))
    await writer.drain()
    writer.close()


async def main():
    port = int(os.getenv("MCP_SERVER_PORT", "8001"))
    server = await asyncio.start_server(handle_request, "0.0.0.0", port)
    print(f"MCP Server listening on port {port}")
    print(f"Registered tools: {list(TOOLS.keys())}")
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
