from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from sowork_kicker.engine import VerificationEngine
from sowork_kicker.models import MessageEvent, VerificationResult, VerificationStatus


class FakeClient:
    def __init__(self):
        self.sent = []
        self.session_id = "s-1"
        self.disconnected = []
        self.responses = []
        self.read_errors = 0
        self.members = [
            {"user_id": "u-1", "display_name": "Alice", "connected": True},
            {"user_id": "u-2", "display_name": "Bob", "connected": True},
            {"user_id": "u-3", "display_name": "Carol", "connected": True},
        ]

    def get_online_users(self):
        return [m for m in self.members if m["connected"]]

    def send_message(self, user, text):
        self.sent.append({"user_id": user["user_id"], "text": text})
        return {"message_id": f"m-{len(self.sent)}", "conversation_id": "c-1"}

    def fetch_responses(self, conversation_id, user_id, since):
        if self.read_errors:
            self.read_errors -= 1
            raise RuntimeError("read failed")
        return [
            msg for msg in self.responses
            if msg["conversation_id"] == conversation_id
            and msg["user_id"] == user_id
            and msg["timestamp"] >= since
        ]

    def disconnect_user(self, user_id):
        self.disconnected.append({"user_id": user_id, "timestamp": datetime.now(timezone.utc)})
        return True

    def is_user_connected(self, user_id):
        return next((m["connected"] for m in self.members if m["user_id"] == user_id), False)


class VerificationEngineTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)

    def _engine(self, client, *, timeout_seconds=60, simulation=True):
        return VerificationEngine(
            client,
            message_template="Please reply to confirm you are online.",
            timeout_seconds=timeout_seconds,
            simulation=simulation,
            clock=lambda: self.now,
            sleep=lambda *_: None,
        )

    def test_response_within_timeout_cancels_disconnect(self):
        client = FakeClient()
        engine = self._engine(client)
        user = client.members[0]

        client.responses = [
            {
                "conversation_id": "c-1",
                "user_id": user["user_id"],
                "text": "Please reply to confirm you are online.",
                "timestamp": self.now + timedelta(seconds=10),
            }
        ]

        result = engine.run_single_user(user)

        self.assertEqual(result.status, VerificationStatus.CANCELLED)
        self.assertEqual(client.disconnected, [])

    def test_old_or_other_user_message_does_not_count(self):
        client = FakeClient()
        engine = self._engine(client)
        user = client.members[0]
        other_user = client.members[1]

        session = engine.start_verification(user)
        self.now += timedelta(seconds=121)

        client.responses = [
            {
                "conversation_id": "c-1",
                "user_id": other_user["user_id"],
                "text": "Please reply to confirm you are online.",
                "timestamp": self.now + timedelta(seconds=15),
            },
            {
                "conversation_id": "c-1",
                "user_id": user["user_id"],
                "text": "Old message",
                "timestamp": self.now - timedelta(seconds=5),
            },
        ]

        result = engine.evaluate_session(session)

        self.assertEqual(result.status, VerificationStatus.EXPIRED)
        self.assertEqual(len(client.disconnected), 0 if engine.simulation else 1)

    def test_no_response_in_simulation_logs_disconnect_candidate(self):
        client = FakeClient()
        engine = self._engine(client, simulation=True)
        user = client.members[0]

        session = engine.start_verification(user)
        self.now += timedelta(seconds=121)

        result = engine.evaluate_session(session)

        self.assertEqual(result.status, VerificationStatus.EXPIRED)
        self.assertEqual(client.disconnected, [])
        self.assertIn("would_disconnect", result.details)

    def test_read_failure_blocks_disconnect(self):
        client = FakeClient()
        engine = self._engine(client, simulation=False)
        user = client.members[0]
        client.read_errors = 1

        result = engine.run_single_user(user)

        self.assertEqual(result.status, VerificationStatus.ERROR)
        self.assertEqual(client.disconnected, [])

    def test_logout_and_reconnect_should_not_reuse_old_verification(self):
        client = FakeClient()
        engine = self._engine(client, simulation=False)
        user = client.members[0]

        first = engine.start_verification(user)
        user["connected"] = False
        engine.on_user_left(user["user_id"])
        user["connected"] = True
        second = engine.start_verification(user)

        self.assertNotEqual(first.session_id, second.session_id)
        self.assertEqual(first.status, VerificationStatus.CANCELLED)
        self.assertEqual(second.status, VerificationStatus.ACTIVE)

    def test_duplicate_checks_do_not_trigger_duplicate_actions(self):
        client = FakeClient()
        engine = self._engine(client, simulation=False)
        user = client.members[0]

        first = engine.start_verification(user)
        second = engine.start_verification(user)

        self.assertEqual(first.session_id, second.session_id)
        self.assertEqual(len(client.sent), 1)


if __name__ == "__main__":
    unittest.main()
