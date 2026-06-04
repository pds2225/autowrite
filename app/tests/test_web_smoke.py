from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from auto_write.main import app


class WebSmokeTests(unittest.TestCase):
    def test_home_page(self):
        client = TestClient(app)
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Auto Write", response.text)

    def test_health_payload_has_backward_compatible_key(self):
        client = TestClient(app)
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("ai_available", body)
        self.assertIn("openai_available", body)
        self.assertEqual(body["ai_available"], body["openai_available"])


if __name__ == "__main__":
    unittest.main()
