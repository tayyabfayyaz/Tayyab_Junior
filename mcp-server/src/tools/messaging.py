"""T049: MCP whatsapp_send tool — send WhatsApp messages via Business API."""

import os
import time

import httpx

from mcp_server.src.logger import MCPLogger

logger = MCPLogger()


def whatsapp_send(to: str, message: str, task_id: str = "unknown") -> dict:
    """Send a WhatsApp message via the WhatsApp Business API."""
    start = time.time()
    access_token = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
    phone_id = os.getenv("WHATSAPP_PHONE_ID", "")

    if not access_token or not phone_id:
        result = {"status": "error", "error": "WhatsApp credentials not configured"}
        duration_ms = int((time.time() - start) * 1000)
        logger.log_invocation(task_id, "whatsapp_send", {"to": to}, result, "error", duration_ms)
        return result

    try:
        url = f"https://graph.facebook.com/v18.0/{phone_id}/messages"
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": message},
        }

        with httpx.Client() as client:
            response = client.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()

        result = {
            "status": "sent",
            "message_id": data.get("messages", [{}])[0].get("id", "unknown"),
        }
        status = "success"
    except Exception as e:
        result = {"status": "error", "error": str(e)}
        status = "error"

    duration_ms = int((time.time() - start) * 1000)
    logger.log_invocation(task_id, "whatsapp_send", {"to": to, "message": message[:50]}, result, status, duration_ms)
    return result
