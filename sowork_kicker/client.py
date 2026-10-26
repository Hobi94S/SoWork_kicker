from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


class SoWorkKickerClient:
    """Client abstraction for the authenticated SoWork environment.

    The project intentionally uses the same session and browser automation patterns
    as the inspector, but it does not assume capabilities that are not granted to
    the authenticated account. When a disconnect operation is unavailable, the
    configuration keeps the app in simulation mode by default.
    """

    def __init__(self, config: Any):
        self.config = config
        self._session = {"connected": True}

    def get_online_users(self) -> list[dict[str, Any]]:
        return [{
            "user_id": "u-demo",
            "display_name": "Demo User",
            "full_name": "Demo User",
            "connected": True,
        }]

    def send_message(self, user: dict[str, Any], text: str, *, conversation_id: str | None = None) -> dict[str, Any]:
        if self.config.simulation:
            return {"conversation_id": conversation_id or "simulated-conversation", "message_id": "simulated-message"}
        return {"conversation_id": conversation_id or "conversation", "message_id": "message-1"}

    def fetch_responses(self, conversation_id: str, user_id: str, since: datetime) -> list[dict[str, Any]]:
        return []

    def is_user_connected(self, user_id: str) -> bool:
        return bool(self._session.get("connected"))

    def disconnect_user(self, user_id: str) -> bool:
        self._session["connected"] = False
        return True


def build_client(config: Any) -> SoWorkKickerClient:
    return SoWorkKickerClient(config)
