from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class VerificationStatus(str, Enum):
    ACTIVE = "active"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    ERROR = "error"


@dataclass
class MessageEvent:
    conversation_id: str
    user_id: str
    text: str
    timestamp: datetime
    message_id: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class VerificationSession:
    session_id: str
    user_id: str
    user: dict[str, Any]
    conversation_id: str
    message_id: str | None
    sent_at: datetime
    deadline: datetime
    status: VerificationStatus = VerificationStatus.ACTIVE
    created_at: datetime | None = None


@dataclass
class VerificationResult:
    session_id: str
    user_id: str
    display_name: str
    status: VerificationStatus
    sent_at: datetime
    deadline: datetime
    completed_at: datetime
    details: dict[str, Any] = field(default_factory=dict)
    response_text: str | None = None
    response_message_id: str | None = None
