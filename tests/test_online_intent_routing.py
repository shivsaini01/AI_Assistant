"""Online intent handling must not invoke the local Ollama model."""

import unittest
from unittest.mock import patch

import intent_parser


class OnlineIntentRoutingTests(unittest.TestCase):
    def test_online_conversation_classification_uses_groq_only(self):
        with patch(
            "ai_providers.generate_groq_text",
            return_value='{"mode":"conversation"}',
        ) as groq, patch.object(
            intent_parser,
            "chat",
            side_effect=AssertionError("Online parsing called local Qwen"),
        ):
            result = intent_parser.parse_user_intent(
                "when does Diwali happen in 2025?",
                provider="online",
            )

        self.assertEqual(result, {"mode": "conversation"})
        groq.assert_called_once()

    def test_online_command_classification_and_extraction_use_groq_only(self):
        with patch(
            "ai_providers.generate_groq_text",
            side_effect=[
                '{"mode":"command"}',
                '{"actions":[{"type":"system_info","info":"date"}]}',
            ],
        ) as groq, patch.object(
            intent_parser,
            "chat",
            side_effect=AssertionError("Online parsing called local Qwen"),
        ):
            result = intent_parser.parse_user_intent(
                "what is today's date",
                provider="online",
            )

        self.assertEqual(
            result,
            {
                "mode": "command",
                "actions": [{"type": "system_info", "info": "date"}],
            },
        )
        self.assertEqual(groq.call_count, 2)


if __name__ == "__main__":
    unittest.main()
