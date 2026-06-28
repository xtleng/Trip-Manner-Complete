from __future__ import annotations

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A single message in a dialog."""
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str


class ChatRequest(BaseModel):
    """Request body for sending a chat message."""
    dialog_id: str | None = None
    message: str
    context: dict | None = None


class DialogSummary(BaseModel):
    """Summary of a dialog for listing."""
    dialog_id: str
    title: str | None = None
    last_message: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class DialogDetail(BaseModel):
    """Full dialog with message history."""
    dialog_id: str
    title: str | None = None
    messages: list[ChatMessage] = []
    created_at: str | None = None
    updated_at: str | None = None
