"""Integration tests for the multi-agent Django app."""

import os
import unittest
from django.test import TestCase, Client


def _has_openai_key() -> bool:
    """Return True if OPENAI_API_KEY is set (for optional Responses API tests)."""
    return bool(os.getenv("OPENAI_API_KEY", "").strip())


class ChatApiTests(TestCase):
    """Covers health, chat, session persistence, course recommendations, and Responses API."""

    def setUp(self):
        self.client = Client()

    def test_health_endpoint(self):
        """Health check should return status=ok and include extra fields."""
        resp = self.client.get("/api/health/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("status"), "ok")
        self.assertIn("time", data)
        self.assertIn("app", data)

    def test_chat_sdk_returns_json(self):
        """Chat endpoint should return a JSON response with expected keys."""
        resp = self.client.post(
            "/api/chat-sdk/",
            data={"message": "Hello"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("response", data)
        self.assertIn("session_id", data)
        self.assertIn("agent", data)

    def test_session_persists_across_messages(self):
        """Session ID should remain consistent when reused in multiple turns."""
        r1 = self.client.post(
            "/api/chat-sdk/",
            data={"message": "Hello"},
            content_type="application/json",
        )
        sid1 = r1.json().get("session_id")
        r2 = self.client.post(
            "/api/chat-sdk/",
            data={"message": "How are you?", "session_id": sid1},
            content_type="application/json",
        )
        sid2 = r2.json().get("session_id")
        self.assertEqual(sid1, sid2)

    def test_courseadvisor_recommends_data_science(self):
        """Data science query should trigger CourseAdvisor recommendations."""
        resp = self.client.post(
            "/api/chat-sdk/",
            data={"message": "I'm interested in data science. What courses should I take next semester?"},
            content_type="application/json",
        )
        data = resp.json()
        text = (data.get("response") or "")
        self.assertTrue(any(code in text for code in ["DS101", "DS201", "DS230", "DS310"]))

    @unittest.skipUnless(_has_openai_key(), "OPENAI_API_KEY required for Responses API test")
    def test_responses_api_summarize_text(self):
        """Verify summarize_text tool via Responses API produces a single-sentence summary."""
        r1 = self.client.post(
            "/api/chat-sdk/",
            data={"message": "I am interested in data science. What courses should I take next semester?"},
            content_type="application/json",
        )
        sid = r1.json().get("session_id")
        r2 = self.client.post(
            "/api/chat-sdk/",
            data={"message": "Summarize your recommendations in one concise sentence.", "session_id": sid},
            content_type="application/json",
        )
        text = (r2.json().get("response") or "").strip()
        self.assertTrue(text)
        self.assertNotIn("\n", text)
        self.assertLess(len(text), 300)
