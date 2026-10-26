from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from .models import MessageEvent, VerificationResult, VerificationSession, VerificationStatus


class VerificationEngine:
    """Core workflow for challenge-based presence verification."""

    def __init__(
        self,
        client: Any,
        *,
        message_template: str,
        timeout_seconds: int = 120,
        simulation: bool = True,
        clock: Callable[[], datetime] | None = None,
        sleep: Callable[[float], None] | None = None,
    ) -> None:
        self.client = client
        self.message_template = message_template
        self.timeout_seconds = timeout_seconds
        self.simulation = simulation
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.sleep = sleep or (lambda *_: None)
        self._active_sessions: dict[str, VerificationSession] = {}

    def start_verification(self, user: dict[str, Any]) -> VerificationSession:
        user_id = str(user.get("user_id") or user.get("id") or "")
        if not user_id:
            raise ValueError("Usuário sem identificador válido: nenhum user_id foi informado.")
        active = self._active_sessions.get(user_id)
        if active is not None:
            return active

        sent_at = self.clock()
        text = self.message_template
        conversation_id = str(user.get("conversation_id") or f"conv-{uuid.uuid4().hex}")
        try:
            response = self.client.send_message(user, text, conversation_id=conversation_id)
        except TypeError:
            response = self.client.send_message(user, text)
        if isinstance(response, dict):
            if not conversation_id or response.get("conversation_id"):
                conversation_id = str(response.get("conversation_id") or conversation_id)
            message_id = str(response.get("message_id") or response.get("id") or None)
        else:
            message_id = None

        deadline = sent_at + timedelta(seconds=self.timeout_seconds)
        session = VerificationSession(
            session_id=f"vr-{uuid.uuid4().hex}",
            user_id=user_id,
            user=user,
            conversation_id=conversation_id,
            message_id=message_id,
            sent_at=sent_at,
            deadline=deadline,
            status=VerificationStatus.ACTIVE,
            created_at=sent_at,
        )
        self._active_sessions[user_id] = session
        return session

    def on_user_left(self, user_id: str) -> VerificationSession | None:
        session = self._active_sessions.pop(str(user_id), None)
        if session is None:
            return None
        session.status = VerificationStatus.CANCELLED
        return session

    def run_single_user(self, user: dict[str, Any]) -> VerificationResult:
        session = self.start_verification(user)
        return self.evaluate_session(session)

    def evaluate_session(self, session: VerificationSession) -> VerificationResult:
        user = session.user
        now = self.clock()
        if not self.client.is_user_connected(session.user_id):
            self._active_sessions.pop(session.user_id, None)
            return VerificationResult(
                session_id=session.session_id,
                user_id=session.user_id,
                display_name=str(user.get("display_name") or user.get("full_name") or user.get("name") or session.user_id),
                status=VerificationStatus.CANCELLED,
                sent_at=session.sent_at,
                deadline=session.deadline,
                completed_at=now,
                details={"reason": "user_logged_out"},
            )

        try:
            events = self.client.fetch_responses(session.conversation_id, session.user_id, session.sent_at)
        except Exception as exc:  # fail closed: do not infer absence of response
            self._active_sessions.pop(session.user_id, None)
            return VerificationResult(
                session_id=session.session_id,
                user_id=session.user_id,
                display_name=str(user.get("display_name") or user.get("full_name") or user.get("name") or session.user_id),
                status=VerificationStatus.ERROR,
                sent_at=session.sent_at,
                deadline=session.deadline,
                completed_at=now,
                details={"error": str(exc), "read_failed": True},
            )

        valid = self._filter_valid_responses(session, events)
        if valid:
            self._active_sessions.pop(session.user_id, None)
            msg = valid[0]
            return VerificationResult(
                session_id=session.session_id,
                user_id=session.user_id,
                display_name=str(user.get("display_name") or user.get("full_name") or user.get("name") or session.user_id),
                status=VerificationStatus.CANCELLED,
                sent_at=session.sent_at,
                deadline=session.deadline,
                completed_at=msg.timestamp,
                details={"message_id": msg.message_id, "response_received": True},
                response_text=msg.text,
                response_message_id=msg.message_id,
            )

        if now < session.deadline:
            return VerificationResult(
                session_id=session.session_id,
                user_id=session.user_id,
                display_name=str(user.get("display_name") or user.get("full_name") or user.get("name") or session.user_id),
                status=VerificationStatus.ACTIVE,
                sent_at=session.sent_at,
                deadline=session.deadline,
                completed_at=now,
                details={"waiting_for_response": True},
            )

        self._active_sessions.pop(session.user_id, None)
        if self.simulation:
            return VerificationResult(
                session_id=session.session_id,
                user_id=session.user_id,
                display_name=str(user.get("display_name") or user.get("full_name") or user.get("name") or session.user_id),
                status=VerificationStatus.EXPIRED,
                sent_at=session.sent_at,
                deadline=session.deadline,
                completed_at=now,
                details={"would_disconnect": True, "reason": "no_valid_response_within_timeout"},
            )

        connected = self.client.is_user_connected(session.user_id)
        disconnected = False
        if connected:
            try:
                self.client.disconnect_user(session.user_id)
                disconnected = True
            except Exception as exc:
                return VerificationResult(
                    session_id=session.session_id,
                    user_id=session.user_id,
                    display_name=str(user.get("display_name") or user.get("full_name") or user.get("name") or session.user_id),
                    status=VerificationStatus.ERROR,
                    sent_at=session.sent_at,
                    deadline=session.deadline,
                    completed_at=now,
                    details={"error": str(exc), "disconnect_attempt_failed": True},
                )

        return VerificationResult(
            session_id=session.session_id,
            user_id=session.user_id,
            display_name=str(user.get("display_name") or user.get("full_name") or user.get("name") or session.user_id),
            status=VerificationStatus.EXPIRED,
            sent_at=session.sent_at,
            deadline=session.deadline,
            completed_at=now,
            details={
                "disconnected": disconnected,
                "reason": "no_valid_response_within_timeout",
                "user_connected_before_disconnect": connected,
            },
        )

    def _filter_valid_responses(self, session: VerificationSession, events: list[dict[str, Any]]) -> list[MessageEvent]:
        valid: list[MessageEvent] = []
        for event in events:
            message = dict(event)
            message_id = str(message.get("message_id") or message.get("id") or None)
            timestamp = message.get("timestamp")
            if not isinstance(timestamp, datetime):
                try:
                    timestamp = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
                except (TypeError, ValueError):
                    continue
            if message.get("conversation_id") != session.conversation_id:
                continue
            if str(message.get("user_id") or message.get("sender_id") or "") != session.user_id:
                continue
            if timestamp < session.sent_at:
                continue
            text = str(message.get("text") or "")
            if not text:
                continue
            match = self._response_matches(text)
            if match:
                valid.append(
                    MessageEvent(
                        conversation_id=session.conversation_id,
                        user_id=session.user_id,
                        text=text,
                        timestamp=timestamp,
                        message_id=message_id,
                        raw=message,
                    )
                )
        valid.sort(key=lambda item: item.timestamp)
        return valid

    def _response_matches(self, text: str) -> bool:
        normalized = text.strip().lower()
        template = self.message_template.strip().lower()
        if not normalized:
            return False
        if normalized == template:
            return True
        if template in normalized:
            return True
        return False

    @property
    def active_sessions(self) -> dict[str, VerificationSession]:
        return dict(self._active_sessions)
