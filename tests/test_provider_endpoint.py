"""HTTP contract for the provider selector."""

import unittest
from unittest.mock import patch

import web_server
from ai_providers import ModelRequestError


class ProviderEndpointTests(unittest.TestCase):
    def setUp(self):
        self.client = web_server.app.test_client()

    def test_home_shows_four_provider_choices_and_migrates_legacy_setting(self):
        page = self.client.get("/").get_data(as_text=True)
        for provider in ("groq", "deepseek", "gemini", "local"):
            self.assertIn(f'<option value="{provider}">', page)
        self.assertIn("jarvis.ai.provider.v1", page)
        self.assertIn("jarvis.ai.mode.v1", page)
        self.assertIn('JSON.stringify({ command: text, provider: submittedProvider })', page)

    def test_all_provider_ids_are_forwarded_and_returned(self):
        for provider in ("groq", "deepseek", "gemini", "local"):
            with self.subTest(provider=provider), patch.object(
                web_server, "process_user_input", return_value=("answer", provider)
            ) as process:
                response = self.client.post("/command", json={"command": "hello", "provider": provider})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.get_json(), {"success": True, "message": "answer", "provider": provider})
            process.assert_called_once_with("hello", provider=provider, include_provider=True)

    def test_invalid_or_missing_provider_is_rejected(self):
        for body in ({"command": "hello"}, {"command": "hello", "provider": "other"}):
            response = self.client.post("/command", json=body)
            self.assertEqual(response.status_code, 400)

    def test_failed_qwen_fallback_reports_local_effective_provider(self):
        with patch.object(web_server, "process_user_input", side_effect=ModelRequestError("local failed", "local")):
            response = self.client.post("/command", json={"command": "hello", "provider": "gemini"})
        self.assertEqual(response.status_code, 500)
        self.assertFalse(response.get_json()["success"])
        self.assertEqual(response.get_json()["provider"], "local")


if __name__ == "__main__":
    unittest.main()
