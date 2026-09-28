"""Provider adapters use server credentials and normalized requests."""

import os
import sys
import types
import unittest
from unittest.mock import patch

import ai_providers


class ProviderAdapterTests(unittest.TestCase):
    def test_groq_uses_environment_and_browser_search_only_when_requested(self):
        requests = []

        class FakeCompletions:
            def create(self, **kwargs):
                requests.append(kwargs)
                message = types.SimpleNamespace(content="Groq answer")
                return types.SimpleNamespace(choices=[types.SimpleNamespace(message=message)])

        client = types.SimpleNamespace(chat=types.SimpleNamespace(completions=FakeCompletions()))
        module = types.SimpleNamespace(Groq=lambda **kwargs: self.assertEqual(kwargs["api_key"], "groq-secret") or client)
        with patch.dict(os.environ, {"GROQ_API_KEY": "groq-secret", "GROQ_MODEL": "groq-test"}), patch.dict(sys.modules, {"groq": module}):
            self.assertEqual(ai_providers.generate_provider_text("groq", "system", "question"), "Groq answer")
            self.assertEqual(ai_providers.generate_provider_text("groq", "system", "question", web_search=True), "Groq answer")
        self.assertEqual(requests[0]["model"], "groq-test")
        self.assertNotIn("tools", requests[0])
        self.assertEqual(requests[1]["tools"], [{"type": "browser_search"}])
        self.assertEqual(requests[1]["tool_choice"], "auto")

    def test_deepseek_uses_openai_compatible_client_and_server_key(self):
        requests = []

        class Completions:
            def create(self, **kwargs):
                requests.append(kwargs)
                return types.SimpleNamespace(choices=[types.SimpleNamespace(message=types.SimpleNamespace(content="DeepSeek answer"))])

        client = types.SimpleNamespace(chat=types.SimpleNamespace(completions=Completions()))
        def make_client(**kwargs):
            self.assertEqual(kwargs, {"api_key": "deepseek-secret", "base_url": "https://api.deepseek.com"})
            return client
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "deepseek-secret", "DEEPSEEK_MODEL": "deepseek-test"}), patch.dict(sys.modules, {"openai": types.SimpleNamespace(OpenAI=make_client)}):
            self.assertEqual(ai_providers.generate_provider_text("deepseek", "system", "question", web_search=True), "DeepSeek answer")
        self.assertEqual(requests[0]["model"], "deepseek-test")
        self.assertEqual(requests[0]["messages"], [{"role": "system", "content": "system"}, {"role": "user", "content": "question"}])
        self.assertNotIn("tools", requests[0])

    def test_gemini_uses_google_genai_client_and_server_key(self):
        requests = []
        configs = []

        class Models:
            def generate_content(self, **kwargs):
                requests.append(kwargs)
                return types.SimpleNamespace(text="Gemini answer")

        def make_client(**kwargs):
            self.assertEqual(kwargs, {"api_key": "gemini-secret"})
            return types.SimpleNamespace(models=Models())
        def make_config(**kwargs):
            configs.append(kwargs)
            return kwargs
        genai = types.SimpleNamespace(Client=make_client, types=types.SimpleNamespace(GenerateContentConfig=make_config))
        with patch.dict(os.environ, {"GEMINI_API_KEY": "gemini-secret", "GEMINI_MODEL": "gemini-test"}), patch.dict(sys.modules, {"google": types.SimpleNamespace(genai=genai)}):
            self.assertEqual(ai_providers.generate_provider_text("gemini", "system", "question", web_search=True), "Gemini answer")
        self.assertEqual(requests[0]["model"], "gemini-test")
        self.assertEqual(requests[0]["contents"], "question")
        self.assertEqual(configs, [{"system_instruction": "system"}])
        self.assertEqual(requests[0]["config"], configs[0])
        self.assertNotIn("tools", requests[0])

    def test_missing_key_error_does_not_expose_secret(self):
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": ""}):
            with self.assertRaises(ai_providers.ProviderConfigurationError) as raised:
                ai_providers.generate_provider_text("deepseek", "system", "question")
        self.assertNotIn("secret", str(raised.exception))

    def test_empty_provider_text_is_rejected(self):
        client = types.SimpleNamespace(chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=lambda **kwargs: types.SimpleNamespace(choices=[]))))
        with patch.dict(os.environ, {"GROQ_API_KEY": "test"}), patch.dict(sys.modules, {"groq": types.SimpleNamespace(Groq=lambda **kwargs: client)}):
            with self.assertRaises(ai_providers.ProviderRequestError):
                ai_providers.generate_provider_text("groq", "system", "question")

    def test_quota_errors_are_sanitized_and_include_http_status(self):
        class QuotaError(RuntimeError):
            status_code = 429

        def fail_request(**kwargs):
            raise QuotaError("request included private-key-value")

        client = types.SimpleNamespace(chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=fail_request)))
        with patch.dict(os.environ, {"GROQ_API_KEY": "private-key-value"}), patch.dict(
            sys.modules, {"groq": types.SimpleNamespace(Groq=lambda **kwargs: client)}
        ):
            with self.assertRaises(ai_providers.ProviderRequestError) as raised:
                ai_providers.generate_provider_text("groq", "system", "question")
        self.assertIn("429", str(raised.exception))
        self.assertNotIn("private-key-value", str(raised.exception))

    def test_auth_model_timeout_and_connectivity_failures_are_sanitized(self):
        cases = (
            (401, "rejected the API key"),
            (403, "rejected the API key"),
            (404, "model was not found"),
            (429, "rate limit reached"),
            (TimeoutError("private-key-value"), "timed out"),
            (ConnectionError("private-key-value"), "connect to Deepseek"),
        )
        for failure, expected in cases:
            with self.subTest(failure=failure):
                if isinstance(failure, int):
                    error_type = type("ProviderFailure", (RuntimeError,), {"status_code": failure})
                    failure_error = error_type("private-key-value")
                else:
                    failure_error = failure
                client = types.SimpleNamespace(
                    chat=types.SimpleNamespace(
                        completions=types.SimpleNamespace(create=lambda **kwargs: (_ for _ in ()).throw(failure_error))
                    )
                )
                with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "private-key-value"}), patch.dict(
                    sys.modules,
                    {"openai": types.SimpleNamespace(OpenAI=lambda **kwargs: client)},
                ):
                    with self.assertRaises(ai_providers.ProviderRequestError) as raised:
                        ai_providers.generate_provider_text("deepseek", "system", "question")
                self.assertIn(expected, str(raised.exception))
                self.assertNotIn("private-key-value", str(raised.exception))

    def test_missing_sdk_is_reported_as_actionable_configuration_error(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "configured-key"}), patch.dict(
            sys.modules, {"google": None}
        ):
            with self.assertRaises(ai_providers.ProviderConfigurationError) as raised:
                ai_providers.generate_provider_text("gemini", "system", "question")
        self.assertIn("Google GenAI SDK is not installed", str(raised.exception))
        self.assertNotIn("configured-key", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
