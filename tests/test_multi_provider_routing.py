"""Routing regressions for the multi-provider web selection."""

import unittest
from unittest.mock import patch

import intent_parser
import assistant
from ai_providers import ProviderRequestError


class ProviderIntentRoutingTests(unittest.TestCase):
    def test_each_cloud_provider_routes_classifier_and_actions_through_adapter(self):
        for provider in ("groq", "deepseek", "gemini"):
            with self.subTest(provider=provider), patch(
                "ai_providers.generate_provider_text",
                side_effect=['{"mode":"command"}', '{"actions":[{"type":"system_info","info":"date"}]}'],
            ) as cloud_call, patch.object(
                intent_parser,
                "chat",
                side_effect=AssertionError("cloud intent used local Qwen"),
            ):
                parsed = intent_parser.parse_user_intent("what is today's date", provider=provider)
            self.assertEqual(parsed["mode"], "command")
            self.assertEqual(cloud_call.call_count, 2)
            self.assertTrue(all(call.kwargs.get("web_search") is False for call in cloud_call.call_args_list))

    def test_malformed_cloud_json_is_reported_to_assistant(self):
        with patch("ai_providers.generate_provider_text", return_value="not json"):
            with self.assertRaises(Exception):
                intent_parser.parse_user_intent("who are you", provider="deepseek")

    def test_cloud_command_without_actions_is_reported_to_assistant(self):
        with patch(
            "ai_providers.generate_provider_text",
            side_effect=['{"mode":"command"}', "{}"],
        ):
            with self.assertRaises(ProviderRequestError):
                intent_parser.parse_user_intent("open the app", provider="groq")

    def test_local_provider_uses_qwen_and_never_cloud(self):
        response = {"message": {"content": '{"mode":"conversation"}'}}
        with patch.object(intent_parser, "chat", return_value=response) as local_call, patch(
            "ai_providers.generate_provider_text",
            side_effect=AssertionError("local intent called cloud"),
        ):
            result = intent_parser.parse_user_intent("who are you")
        self.assertEqual(result, {"mode": "conversation"})
        local_call.assert_called_once()


class AssistantProviderRoutingTests(unittest.TestCase):
    def test_each_cloud_provider_generates_chat_without_calling_qwen(self):
        for provider in ("groq", "deepseek", "gemini"):
            with self.subTest(provider=provider), patch(
                "ai_providers.generate_provider_text", return_value=f"{provider} answer"
            ) as cloud_call, patch.object(
                assistant, "chat", side_effect=AssertionError("cloud answer used Qwen")
            ):
                answer, actual = assistant.ask_ai_with_provider("hello", "context", provider)
            self.assertEqual((answer, actual), (f"{provider} answer", provider))
            self.assertEqual(cloud_call.call_args.kwargs["web_search"], provider == "groq")

    def test_cloud_failure_falls_back_to_qwen_and_reports_local(self):
        with patch(
            "ai_providers.generate_provider_text",
            side_effect=ProviderRequestError("gemini", "Gemini unavailable."),
        ), patch.object(
            assistant, "chat", return_value={"message": {"content": "Qwen answer"}}
        ) as local_call:
            answer, actual = assistant.ask_ai_with_provider("hello", "", "gemini")
        self.assertIn("Gemini unavailable", answer)
        self.assertIn("Qwen answer", answer)
        self.assertEqual(actual, "local")
        local_call.assert_called_once()

    def test_legacy_console_entry_point_returns_a_string_and_defaults_local(self):
        with patch.object(assistant, "_process_user_input", return_value="local response") as process:
            response = assistant.process_user_input("hello")
        self.assertEqual(response, "local response")
        process.assert_called_once_with("hello", provider=None)

    def test_parser_failure_restarts_full_request_on_qwen(self):
        with patch.object(
            assistant,
            "parse_user_intent",
            side_effect=[ProviderRequestError("gemini", "Gemini is unavailable."), {"mode": "conversation"}],
        ) as parser, patch.object(
            assistant, "build_context_with_metadata", return_value=""
        ), patch.object(
            assistant, "get_last_command_context", return_value=None
        ), patch.object(
            assistant, "ask_ai", return_value="Qwen answer"
        ), patch.object(assistant, "remember"):
            response, effective = assistant.process_user_input(
                "who are you", provider="gemini", include_provider=True
            )
        self.assertEqual(effective, "local")
        self.assertIn("Gemini is unavailable", response)
        self.assertIn("Qwen answer", response)
        self.assertEqual(
            [call.kwargs["provider"] for call in parser.call_args_list],
            ["gemini", "local"],
        )

    def test_answer_failure_restarts_intent_and_answer_on_qwen(self):
        def answer_side_effect(_text, _context, provider="local", raise_errors=False):
            if provider == "groq":
                raise ProviderRequestError("groq", "Groq unavailable.")
            return "Qwen answer"

        with patch.object(
            assistant, "parse_user_intent", return_value={"mode": "conversation"}
        ) as parser, patch.object(
            assistant, "build_context_with_metadata", return_value=""
        ), patch.object(
            assistant, "get_last_command_context", return_value=None
        ), patch.object(
            assistant, "ask_ai", side_effect=answer_side_effect
        ), patch.object(assistant, "remember"):
            response, effective = assistant.process_user_input(
                "who are you", provider="groq", include_provider=True
            )
        self.assertEqual(effective, "local")
        self.assertIn("Groq unavailable", response)
        self.assertIn("Qwen answer", response)
        self.assertEqual([call.kwargs["provider"] for call in parser.call_args_list], ["groq", "local"])

    def test_cloud_fallback_failure_always_reports_local_provider(self):
        with patch.object(
            assistant,
            "parse_user_intent",
            side_effect=[ProviderRequestError("gemini", "Gemini unavailable."), RuntimeError("local parse failed")],
        ), patch.object(
            assistant, "build_context_with_metadata", return_value=""
        ), patch.object(
            assistant, "get_last_command_context", return_value=None
        ):
            with self.assertRaises(assistant.ModelRequestError) as raised:
                assistant.process_user_input("who are you", provider="gemini", include_provider=True)
        self.assertEqual(raised.exception.effective_provider, "local")

    def test_local_failure_after_cloud_error_reports_local_effective_provider(self):
        with patch(
            "ai_providers.generate_provider_text",
            side_effect=ProviderRequestError("deepseek", "DeepSeek unavailable."),
        ), patch.object(assistant, "chat", side_effect=RuntimeError("qwen down")):
            with self.assertRaises(assistant.ModelRequestError) as raised:
                assistant.ask_ai_with_provider("hello", "", "deepseek")
        self.assertEqual(raised.exception.effective_provider, "local")

    def test_deterministic_greeting_does_not_call_a_model(self):
        with patch.object(assistant, "parse_user_intent", side_effect=AssertionError("greeting used a model")):
            response = assistant.process_user_input("hi", provider="groq", include_provider=True)
        self.assertEqual(response, ("Hey! How can I help?", "groq"))

    def test_chat_action_uses_the_selected_provider_router(self):
        with patch.object(
            assistant, "ask_ai_with_provider", return_value=("DeepSeek response", "deepseek")
        ) as answer, patch.object(assistant, "handle_chat") as local_chat:
            processed, effective = assistant.process_actions(
                {"actions": [{"type": "chat", "text": "a question"}]},
                response_mode="deepseek",
                conversation_context="context",
            )
        self.assertTrue(processed)
        self.assertEqual(effective, "deepseek")
        answer.assert_called_once_with("a question", "context", "deepseek")
        local_chat.assert_not_called()

    def test_cloud_chat_fails_before_external_actions_can_run_twice(self):
        with patch.object(
            assistant,
            "ask_ai_with_provider",
            side_effect=ProviderRequestError("groq", "Groq unavailable."),
        ), patch.object(assistant, "handle_launch_apps") as launch:
            with self.assertRaises(ProviderRequestError):
                assistant.process_actions(
                    {"actions": [
                        {"type": "launch_app", "apps": ["example"]},
                        {"type": "chat", "text": "explain this"},
                    ]},
                    response_mode="groq",
                    fallback_on_cloud_error=False,
                )
        launch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
