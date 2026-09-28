"""Server-side adapters for Jarvis cloud model providers."""

import os


class ProviderConfigurationError(RuntimeError):
    """A provider cannot be used because its key or SDK is unavailable."""

    def __init__(self, provider: str, public_message: str):
        super().__init__(public_message)
        self.provider = provider
        self.public_message = public_message


class ProviderRequestError(RuntimeError):
    """A provider request failed; the message is safe to show to users."""

    def __init__(self, provider: str, public_message: str):
        super().__init__(public_message)
        self.provider = provider
        self.public_message = public_message


class GroqConfigurationError(ProviderConfigurationError):
    def __init__(self, public_message: str):
        super().__init__("groq", public_message)


class GroqRequestError(ProviderRequestError):
    def __init__(self, public_message: str):
        super().__init__("groq", public_message)


class ModelRequestError(RuntimeError):
    """Raised when the selected model and local fallback both fail."""

    def __init__(self, message: str, effective_provider: str = "local"):
        super().__init__(message)
        self.effective_provider = effective_provider
        # Kept for callers from the earlier online/offline interface.
        self.effective_mode = "offline" if effective_provider == "local" else "online"


_PROVIDERS = {
    "groq": ("GROQ_API_KEY", "GROQ_MODEL", "openai/gpt-oss-120b"),
    "deepseek": ("DEEPSEEK_API_KEY", "DEEPSEEK_MODEL", "deepseek-flash"),
    "gemini": ("GEMINI_API_KEY", "GEMINI_MODEL", "gemini-3.8-flash"),
}


def _configuration(provider):
    key_name, model_name, default_model = _PROVIDERS[provider]
    api_key = os.environ.get(key_name, "").strip()
    if not api_key:
        message = f"{key_name} is missing. Set it in the terminal that starts web_server.py."
        if provider == "groq":
            raise GroqConfigurationError(message)
        raise ProviderConfigurationError(provider, message)
    return api_key, os.environ.get(model_name, default_model).strip() or default_model


def _request_error(provider, error):
    status = getattr(error, "status_code", None) or getattr(error, "status", None)
    try:
        status = int(status)
    except (TypeError, ValueError):
        status = None

    label = provider.title()
    error_name = type(error).__name__.lower()
    if status == 429:
        message = f"{label} usage limit or rate limit reached (HTTP 429)."
    elif status in {401, 403}:
        message = f"{label} rejected the API key or its permissions."
    elif status == 404:
        message = f"{label} model was not found; check its model setting."
    elif "timeout" in error_name:
        message = f"{label} request timed out."
    elif "connection" in error_name or "connect" in error_name:
        message = f"Could not connect to {label}."
    elif status is not None:
        message = f"{label} API request failed (HTTP {status})."
    else:
        message = f"{label} API request failed ({type(error).__name__})."
    if provider == "groq":
        return GroqRequestError(message)
    return ProviderRequestError(provider, message)


def _generate_groq(api_key, model, system_prompt, user_text, web_search):
    try:
        from groq import Groq
    except ImportError as error:
        raise GroqConfigurationError("The Groq SDK is not installed. Run pip install -r requirements.txt.") from error
    try:
        client = Groq(api_key=api_key)
        tool_options = {"tools": [{"type": "browser_search"}], "tool_choice": "auto"} if web_search else {}
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_text}],
            **tool_options,
        )
        text = response.choices[0].message.content
    except Exception as error:
        raise _request_error("groq", error) from error
    return text


def _generate_deepseek(api_key, model, system_prompt, user_text):
    try:
        from openai import OpenAI
    except ImportError as error:
        raise ProviderConfigurationError(
            "deepseek", "The OpenAI SDK is not installed. Run pip install -r requirements.txt."
        ) from error
    try:
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_text}],
        )
        text = response.choices[0].message.content
    except Exception as error:
        raise _request_error("deepseek", error) from error
    return text


def _generate_gemini(api_key, model, system_prompt, user_text):
    try:
        from google import genai
    except ImportError as error:
        raise ProviderConfigurationError(
            "gemini", "The Google GenAI SDK is not installed. Run pip install -r requirements.txt."
        ) from error
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model,
            contents=user_text,
            config=genai.types.GenerateContentConfig(system_instruction=system_prompt),
        )
        text = response.text
    except Exception as error:
        raise _request_error("gemini", error) from error
    return text


def generate_provider_text(provider, system_prompt, user_text, *, web_search=False):
    """Generate text through the requested cloud provider.

    Browser search is intentionally available only on Groq and is enabled
    only when explicitly requested by the caller.
    """
    if provider not in _PROVIDERS:
        raise ValueError("Cloud provider must be 'groq', 'deepseek', or 'gemini'.")
    api_key, model = _configuration(provider)
    try:
        if provider == "groq":
            text = _generate_groq(api_key, model, system_prompt, user_text, web_search)
        elif provider == "deepseek":
            text = _generate_deepseek(api_key, model, system_prompt, user_text)
        else:
            text = _generate_gemini(api_key, model, system_prompt, user_text)
    except (ProviderConfigurationError, ProviderRequestError):
        raise
    except Exception as error:
        raise _request_error(provider, error) from error
    if not isinstance(text, str) or not text.strip():
        raise ProviderRequestError(provider, f"{provider.title()} returned an empty response.")
    return text.strip()


def generate_groq_text(system_prompt, user_text, web_search=False):
    """Backward-compatible Groq adapter used by existing integrations."""
    return generate_provider_text("groq", system_prompt, user_text, web_search=web_search)
