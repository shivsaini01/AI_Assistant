"""Regression tests for model routing inside parsed chat actions."""

import contextlib
import io
import unittest
from unittest.mock import patch

import assistant


class ChatActionRoutingTests(unittest.TestCase):
    def test_online_chat_action_uses_requested_provider_and_reports_effective_mode(self):
        context = "recent conversation context"

        with patch.object(
            assistant,
            "ask_ai_with_mode",
            return_value=("Groq response", "online"),
        ) as routed_answer, patch.object(assistant, "handle_chat") as local_chat:
            with contextlib.redirect_stdout(io.StringIO()):
                processed, effective_mode = assistant.process_actions(
                    {"actions": [{"type": "chat", "text": "a question"}]},
                    response_mode="online",
                    conversation_context=context,
                )

        self.assertTrue(processed)
        self.assertEqual(effective_mode, "online")
        routed_answer.assert_called_once_with("a question", context, "online")
        local_chat.assert_not_called()

    def test_groq_fallback_mode_is_propagated_from_chat_action(self):
        with patch.object(
            assistant,
            "ask_ai_with_mode",
            return_value=("Qwen fallback response", "offline"),
        ):
            with contextlib.redirect_stdout(io.StringIO()):
                processed, effective_mode = assistant.process_actions(
                    {"actions": [{"type": "chat", "text": "a question"}]},
                    response_mode="online",
                    conversation_context="",
                )

        self.assertTrue(processed)
        self.assertEqual(effective_mode, "offline")


if __name__ == "__main__":
    unittest.main()
