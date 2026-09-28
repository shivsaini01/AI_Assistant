"""Browser search is opt-in on the Groq completion request."""

import os
import sys
import types
import unittest
from unittest.mock import patch

import ai_providers


class GroqBrowserSearchTests(unittest.TestCase):
    def _run_provider(self, browser_search):
        recorded = {}

        class FakeCompletions:
            @staticmethod
            def create(**kwargs):
                recorded.update(kwargs)
                message = types.SimpleNamespace(content="Groq answer")
                choice = types.SimpleNamespace(message=message)
                return types.SimpleNamespace(choices=[choice])

        fake_client = types.SimpleNamespace(
            chat=types.SimpleNamespace(
                completions=FakeCompletions(),
            )
        )
        fake_module = types.SimpleNamespace(Groq=lambda **kwargs: fake_client)

        with patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}), patch.dict(
            sys.modules,
            {"groq": fake_module},
        ):
            result = ai_providers.generate_groq_text(
                "system instructions",
                "user question",
                web_search=browser_search,
            )

        return result, recorded

    def test_web_search_adds_groq_browser_tool_in_auto_mode(self):
        result, request = self._run_provider(browser_search=True)

        self.assertEqual(result, "Groq answer")
        self.assertEqual(request["tools"], [{"type": "browser_search"}])
        self.assertEqual(request["tool_choice"], "auto")

    def test_web_search_remains_disabled_for_intent_parser_calls(self):
        result, request = self._run_provider(browser_search=False)

        self.assertEqual(result, "Groq answer")
        self.assertNotIn("tools", request)
        self.assertNotIn("tool_choice", request)


if __name__ == "__main__":
    unittest.main()
