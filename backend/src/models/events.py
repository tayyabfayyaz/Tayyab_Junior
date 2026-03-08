"""T045: Webhook event models — WhatsApp, Email, GitHub Pydantic models."""

from typing import Optional
from pydantic import BaseModel


class WhatsAppMessage(BaseModel):
    from_: str
    text: dict
    timestamp: str

    class Config:
        populate_by_name = True


class WhatsAppChange(BaseModel):
    value: dict


class WhatsAppEntry(BaseModel):
    id: str
    changes: list[WhatsAppChange]


class WhatsAppWebhookPayload(BaseModel):
    object: str
    entry: list[WhatsAppEntry]


class WhatsAppVerification(BaseModel):
    hub_mode: str
    hub_verify_token: str
    hub_challenge: str


class EmailPubSubMessage(BaseModel):
    data: str
    messageId: str
    publishTime: str


class EmailPubSubPayload(BaseModel):
    message: EmailPubSubMessage
    subscription: str


class GitHubWebhookPayload(BaseModel):
    action: Optional[str] = None
    repository: Optional[dict] = None
    sender: Optional[dict] = None
    issue: Optional[dict] = None
    pull_request: Optional[dict] = None
    review: Optional[dict] = None
