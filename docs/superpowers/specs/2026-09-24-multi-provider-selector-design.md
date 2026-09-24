# Multi-Provider Model Selector Design

## Goal

Let web users choose Groq, DeepSeek, Gemini, or local Qwen for each chat request, while preserving local console behavior and the existing cloud-to-Qwen fallback.

## Approved understanding

- The web selector offers Groq, DeepSeek, Gemini, and Local Qwen.
- Groq remains the initial/default cloud choice, preserving the current Online default.
- The console continues to use local Qwen by default.
- Cloud provider API keys remain in the server environment and are never sent to the browser.
- If the selected cloud provider is unavailable or fails, Jarvis uses local Qwen for that request and reports Local Qwen as the effective provider.
- Automatic web search remains Groq-only.

## User experience

Replace the Online/Offline dropdown in `templates/index.html` with provider choices labeled Groq, DeepSeek, Gemini, and Local Qwen. Initialize a new browser session to Groq. Persist the provider choice for the browser tab. Migrate existing saved values `online` to `groq` and `offline` to `local` so users retain their current preference as closely as possible.

Send the selected provider with each `/command` request. The server returns the effective provider. When cloud-to-local fallback succeeds, the response identifies Local Qwen and the dropdown changes to Local Qwen. A subsequent user selection of a cloud provider tries that provider again. If both the selected cloud provider and Qwen fail, return a failed request with Local Qwen as the effective provider; do not claim a successful answer.

The selector represents the requested/effective conversational provider. Deterministic local actions such as greetings or system date retrieval may complete without invoking a language model; they do not silently run Qwen intent classification in a selected cloud provider path.

## Architecture and request flow

1. The browser submits `{command, provider}` to the existing Flask `/command` route.
2. Flask validates `provider` against `groq`, `deepseek`, `gemini`, and `local` and calls the assistant with the selected provider.
3. The assistant uses the selected provider for both intent classification/action extraction and conversational response generation. Local mode uses the existing Qwen/Ollama model for these language tasks.
4. Groq requests use the configured Groq model. Browser search is available only for final conversational answers, never for JSON intent classification or action extraction.
5. DeepSeek requests use the official API's chat-completions-compatible endpoint and configured model. Gemini requests use the Google GenAI SDK and configured model. Neither provider receives a web-search tool in this feature.
6. If a cloud provider fails during intent parsing or answer generation, Jarvis runs the same request through the local Qwen path and reports `local` as the effective provider.
7. Flask returns `{success, message, provider}`. The browser updates its selection only when the response corresponds to the provider submitted with that request, preserving a newer user selection made while a request was in flight.

The assistant owns provider selection and fallback. The web server validates and serializes the request. The browser stores and displays the per-tab provider choice. The console retains its current local Qwen behavior.

## Provider configuration

- Groq: required `GROQ_API_KEY`; optional `GROQ_MODEL`, default `openai/gpt-oss-120b`.
- DeepSeek: required `DEEPSEEK_API_KEY`; optional `DEEPSEEK_MODEL`, default `deepseek-flash`.
- Gemini: required `GEMINI_API_KEY`; optional `GEMINI_MODEL`, default `gemini-3.8-flash`.
- Local Qwen: uses the existing Ollama configuration and model constant.

Missing credentials or SDK dependencies produce a provider-specific, actionable error before local fallback. Provider keys are read only by the server process. They must not appear in source files, frontend code, browser storage, error output, or logs.

## Error handling

- Reject missing or unsupported provider values with HTTP 400.
- On cloud configuration, authentication, quota, network, service, malformed-response, or empty-response failure, run the current request through Qwen and report `local` as effective provider.
- A failed Qwen fallback returns an error response with effective provider `local`.
- Sanitize provider errors before returning them or logging them; never expose API keys or raw request payloads.
- Do not fall back from one cloud provider to another. A failure always falls back to local Qwen, making the choice and any fallback clear to the user.

## Compatibility

- Keep the existing `/command` route and chat payload shape except for replacing the two-value provider field with the four provider IDs.
- Keep `process_user_input(user_text)` usable as a string-returning local Qwen console entry point.
- Keep Offline/Online session values readable during migration so old browser sessions map to Local Qwen/Groq instead of resetting unexpectedly.
- Keep local command execution and existing Qwen behavior available.

## Scope and non-goals

This change adds provider selection and integrations for Groq, DeepSeek, Gemini, and local Qwen to web chat. It does not add provider/model selection to the console, user accounts or cross-device preference sync, a model-discovery endpoint, cloud-to-cloud fallback, or web search for DeepSeek/Gemini. Groq browser search remains enabled only for final conversational answers.

## Acceptance criteria

1. The web UI shows Groq, DeepSeek, Gemini, and Local Qwen options and defaults new sessions to Groq.
2. A stored `online` preference migrates to Groq and `offline` migrates to Local Qwen.
3. Local Qwen selection performs intent handling and responses locally without cloud calls.
4. Groq, DeepSeek, and Gemini selections route intent handling and responses through the chosen provider without invoking local Qwen unless fallback is needed.
5. Groq browser search is available for final chat answers and excluded from JSON intent/action requests.
6. DeepSeek and Gemini requests do not enable web search.
7. Each cloud provider loads its own key/model settings from server-side environment variables.
8. A cloud-provider error falls back to Qwen for the same request, returns an answer, and updates the UI to Local Qwen.
9. If Qwen also fails, the endpoint reports failure and the effective provider remains Local Qwen.
10. A response from an earlier request cannot overwrite a newer provider selection.
11. The console continues to call local Qwen with its existing string-returning API.

## Verification expectations

Use mocked provider clients to verify each provider's request payload, provider-specific routing, key-missing behavior, quota/service fallback, fallback failure, web-search scoping, invalid provider rejection, legacy preference migration, and in-flight UI synchronization. Automated tests must not use live credentials or consume provider quota. Live API checks are not required for acceptance.

## Primary references

- [Groq browser search](https://console.groq.com/docs/tool-use/built-in-tools/browser-search)
- [DeepSeek API model list](https://api-docs.deepseek.com/api/list-models/)
- [DeepSeek chat completions](https://api-docs.deepseek.com/api/create-chat-completion/)
- [Gemini Google Search grounding](https://ai.google.dev/gemini-api/docs/google-search)
- [Gemini API models](https://ai.google.dev/gemini-api/docs/models)
