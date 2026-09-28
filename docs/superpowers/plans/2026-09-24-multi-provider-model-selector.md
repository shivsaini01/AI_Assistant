# Multi-Provider Model Selector Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax.

**Goal:** Let web users select Groq, DeepSeek, Gemini, or local Qwen while keeping cloud credentials server-side and falling back to local Qwen on cloud failures.

**Architecture:** Add a provider adapter interface in `ai_providers.py`, route the chosen provider through intent parsing and assistant response generation, and report the effective provider through Flask to the browser. Keep the console on local Qwen. Preserve Groq-only browser search for final chat answers; parser calls must not use search tools.

**Tech Stack:** Python, Flask, Ollama, Groq SDK, OpenAI-compatible DeepSeek API, Google GenAI SDK, browser JavaScript, `unittest`.

**Spec:** [2026-09-24-multi-provider-selector-design.md](../specs/2026-09-24-multi-provider-selector-design.md)

## Global Constraints

- Offer Groq, DeepSeek, Gemini, and Local Qwen in the web selector.
- Default new web sessions to Groq; preserve the console's local Qwen default.
- Keep API keys in server environment variables and out of browser storage, source, error output, and logs.
- A cloud provider failure falls back to local Qwen for the current request and reports `local` as the effective provider.
- Do not fall back between cloud providers.
- Enable browser search only for Groq final conversational answers, not intent classification/action extraction.
- Keep `process_user_input(user_text)` usable as a string-returning local Qwen console entry point.
- Preserve deterministic local actions (such as greeting/date) without invoking local Qwen for cloud-selected intent parsing.
- Use mocked providers for tests; tests must not make live API requests or consume quota.

## Review Focus

- Missing selected-provider key or SDK: return an actionable cloud setup explanation with the successful local fallback and report `local`.
- Groq/DeepSeek/Gemini intent parsing fails: restart the same request using the local Qwen path rather than mixing providers mid-request.
- Cloud parser returns malformed or empty JSON: treat as provider failure, then use local Qwen.
- A command includes a `chat` action: route that text through the selected provider and propagate a Qwen fallback as `local`.
- A response arrives after the user has changed the dropdown: do not overwrite the newer selection.

## File Map

- Modify `ai_providers.py`: expose a normalized provider API, retain Groq browser search, add DeepSeek and Gemini adapters, sanitize provider errors.
- Modify `intent_parser.py`: accept a provider and use it for classification and action extraction; default to local Qwen for existing callers.
- Modify `assistant.py`: pass the selected provider through intent parsing and chat actions, fallback to Qwen on selected-cloud errors, preserve console behavior.
- Modify `web_server.py`: validate four provider IDs and return the effective provider.
- Modify `templates/index.html`: replace Online/Offline with four choices, migrate old session values, send provider IDs, and synchronize fallback state.
- Create `static/provider_selector.js`: keep provider validation, legacy-value migration, and stale-response handling in testable browser-independent functions.
- Modify `requirements.txt`: add `openai` and `google-genai`; retain existing Flask, Ollama, and Groq dependencies.
- Create `tests/test_provider_adapters.py`: verify API client request options without live calls.
- Create `tests/test_multi_provider_routing.py`: verify intent, answer, fallback, and console routing.
- Create `tests/test_provider_endpoint.py`: verify Flask validation and effective-provider responses.
- Create `tests/test_provider_selector.js`: verify legacy preference migration and in-flight response gating with Node's built-in test runner.
- Create `docs/multi-provider-setup.md`: document server-side key and optional model configuration for each provider.

## Interfaces

- `generate_provider_text(provider: str, system_prompt: str, user_text: str, *, web_search: bool = False) -> str`
- `ProviderConfigurationError(provider: str, public_message: str)` for missing credentials/dependencies.
- `ProviderRequestError(provider: str, public_message: str)` for rejected, failed, empty, or malformed cloud responses.
- `ModelRequestError(message: str, effective_provider: str)` when the chosen path and local fallback both fail.
- `parse_user_intent(user_text: str, conversation_context: str = "", provider: str = "local") -> dict | None`
- `process_user_input(user_text, provider=None, include_provider=False)`: with no provider, retain the console string result; with `include_provider=True`, return `(message, effective_provider)` for Flask.
- `/command` request: `{"command": "...", "provider": "groq|deepseek|gemini|local"}`.
- `/command` response: `{"success": true, "message": "...", "provider": "groq|deepseek|gemini|local"}`.

### Task 1: Normalize provider adapters and add DeepSeek/Gemini

**Files:**
- Modify `ai_providers.py`
- Modify `requirements.txt`
- Create `tests/test_provider_adapters.py`

**Provider defaults:** Groq: `GROQ_MODEL` or `openai/gpt-oss-120b`; DeepSeek: `DEEPSEEK_MODEL` or `deepseek-flash`; Gemini: `GEMINI_MODEL` or `gemini-3.8-flash`.

- [x] Add adapter tests for each provider before changing the implementation. Mock the SDK client constructors and assert model, messages, and API key are passed from the correct environment variable; assert no adapter exposes its key in its public exception.
- [x] Add tests proving `web_search=False` omits `tools` and `tool_choice`, and `web_search=True` adds `[{"type": "browser_search"}]` plus `tool_choice="auto"` only to Groq requests.
- [x] Cover missing-key/SDK configuration, authentication, quota, timeout, malformed SDK response, and empty response with sanitized public errors.
- [x] Include a regression assertion that the Groq request arguments contain the search tool only when enabled:

```python
request = fake_groq.chat.completions.create.call_args.kwargs
assert request.get("tools") == [{"type": "browser_search"}]
assert request.get("tool_choice") == "auto"
```

- [x] Run `python -m unittest discover -s tests -p "test_provider_adapters.py" -v`; confirm the missing normalized adapter fails before implementation.
- [x] Introduce `generate_provider_text(provider, system_prompt, user_text, *, web_search=False)` and shared `ProviderConfigurationError`/`ProviderRequestError` types. Keep provider SDK imports lazy.
- [x] Implement DeepSeek through `OpenAI(api_key=..., base_url="https://api.deepseek.com")` and Gemini through `google.genai.Client`; preserve Groq's existing browser-search option.
- [x] Normalize non-empty text extraction and translate 401/403, 404, 429, timeout, connectivity, malformed response, and empty response into sanitized provider errors.
- [x] Add `openai` and `google-genai` to `requirements.txt`; keep Flask, Ollama, and Groq entries.
- [x] Run `python -m unittest discover -s tests -p "test_provider_adapters.py" -v`; expect all adapter request-shape and error-sanitization cases to pass.

### Task 2: Route intent parsing through the chosen provider

**Files:**
- Modify `intent_parser.py`
- Modify `tests/test_online_intent_routing.py`
- Create or extend `tests/test_multi_provider_routing.py`

**Interfaces:** `classify_message`, `extract_actions`, and `parse_user_intent` accept `provider="local"`. Cloud parser calls use `generate_provider_text(..., web_search=False)`.

- [x] Add tests for Groq, DeepSeek, Gemini, and local parsing: each cloud mode calls its adapter for classification and action extraction, while local mode calls Ollama and no cloud adapter.
- [x] Add tests that malformed JSON, empty model output, and provider errors raise on cloud paths so the assistant can consistently fall back; preserve the local parser's current safe failure behavior.
- [x] Pin cloud parsing to the adapter and prove it does not call Ollama:

```python
with patch.object(ai_providers, "generate_provider_text", create=True,
                  return_value='{"mode":"conversation"}') as cloud_call, \\
     patch.object(intent_parser, "chat",
                  side_effect=AssertionError("cloud path used Ollama")):
    result = intent_parser.parse_user_intent("a normal question", provider="deepseek")
assert result == {"mode": "conversation"}
cloud_call.assert_called_once()
```

- [x] Run `python -m unittest discover -s tests -p "test_online_intent_routing.py" -v` and `python -m unittest discover -s tests -p "test_multi_provider_routing.py" -v`; confirm cloud parsing is not using Ollama and malformed cloud output is observable to the caller.
- [x] Add the provider parameter with default `local`, preserving existing call sites and the parser's command/conversation result shape.
- [x] Route classifier and action-extraction prompts through the selected cloud adapter without enabling search; keep local calls on the existing Qwen model.
- [x] Run the focused parser tests and confirm every cloud provider path avoids local Ollama unless fallback is triggered at the assistant layer.

### Task 3: Implement assistant provider routing and local fallback

**Files:**
- Modify `assistant.py`
- Modify `tests/test_online_chat_routing.py`
- Extend `tests/test_multi_provider_routing.py`

- [x] Add tests for each selected provider generating the chat answer, Groq alone receiving `web_search=True`, local mode invoking Qwen, and cloud failure restarting parsing plus answer generation locally.
- [x] Add regression coverage for parsed `chat` actions and verify a cloud-to-Qwen fallback returns effective provider `local`.
- [x] Cover fallback failure: if Qwen also fails, return an unsuccessful result with effective provider `local` and no fabricated answer.
- [x] Add a compatibility test that `process_user_input("...")` still returns a string and defaults to local Qwen when no provider argument is supplied.
- [x] Run `python -m unittest discover -s tests -p "test_online_chat_routing.py" -v` and `python -m unittest discover -s tests -p "test_multi_provider_routing.py" -v`; confirm the new routing tests fail against the current two-mode implementation.
- [x] Replace the binary Online/Offline assistant router with provider routing. Make the default provider `local` for legacy console callers.
- [x] On any selected-cloud parser or answer failure, repeat the complete request through local Qwen once; do not retry another cloud provider. Return the local answer with an actionable fallback note and effective provider `local`.
- [x] Pass the selected provider into chat actions handled by `process_actions`; retain the local `handle_chat` route for console callers.
- [x] Preserve the string-only console wrapper and return `(message, effective_provider)` only when Flask requests it.
- [x] Run the focused assistant routing tests; confirm successful cloud calls avoid Qwen and failed cloud calls report Local Qwen.

### Task 4: Change Flask provider contract and web selector

**Files:**
- Modify `web_server.py`
- Modify `templates/index.html`
- Create `static/provider_selector.js`
- Create `tests/test_provider_endpoint.py`
- Create `tests/test_provider_selector.js`

- [x] Add Flask tests for all four accepted values, invalid/missing provider HTTP 400 responses, and successful/fallback provider fields.
- [x] Implement `normalizeProvider(value)` so `online` maps to `groq`, `offline` maps to `local`, valid provider IDs pass through, and unknown/empty values map to `groq`. Implement `shouldApplyProviderResponse(currentProvider, submittedProvider)` as an equality check.
- [x] Test those pure functions with Node's built-in test runner:

```javascript
const assert = require("node:assert/strict");
const { test } = require("node:test");
const { normalizeProvider, shouldApplyProviderResponse } = require("../static/provider_selector.js");

test("migrates old selections and ignores stale responses", () => {
  assert.equal(normalizeProvider("online"), "groq");
  assert.equal(normalizeProvider("offline"), "local");
  assert.equal(normalizeProvider("gemini"), "gemini");
  assert.equal(shouldApplyProviderResponse("deepseek", "groq"), false);
});
```

- [x] Run `node --test tests/test_provider_selector.js`; confirm the missing selector helpers fail before implementation.
- [x] Run `python -m unittest discover -s tests -p "test_provider_endpoint.py" -v`; confirm invalid provider values are rejected and the selected provider reaches the assistant stub.
- [x] Validate `provider` against `groq`, `deepseek`, `gemini`, and `local`; return the effective provider as JSON and preserve safe error logging.
- [x] Test successful cloud fallback, failed fallback, and all four provider selections through Flask using assistant stubs; assert HTTP status, `success`, `message`, and effective `provider` for each outcome.
- [x] Replace the Online/Offline choices and labels with Groq, DeepSeek, Gemini, and Local Qwen; persist `jarvis.ai.provider.v1` in session storage and migrate values from `jarvis.ai.mode.v1`.
- [x] Send `{command, provider}` on every request and apply the returned provider only if the user has not changed the dropdown since submitting that request.
- [x] Run `node --test tests/test_provider_selector.js` and the endpoint test; inspect the rendered template for all four options and fallback synchronization.

### Task 5: Document setup and run complete verification

**Files:**
- Create `docs/multi-provider-setup.md`
- Run all tests in `tests/`

- [x] Document PowerShell commands for setting `GROQ_API_KEY`, `DEEPSEEK_API_KEY`, and `GEMINI_API_KEY` in the server process; list optional `GROQ_MODEL`, `DEEPSEEK_MODEL`, and `GEMINI_MODEL`; explain Local Qwen requires Ollama.
- [x] Document that only Groq currently has automatic browser search in this feature and that cloud failures switch the current request to Local Qwen.
- [x] Run `python -m unittest discover -s tests -v` and `node --test tests/test_provider_selector.js`; expect all provider, parser, assistant, endpoint, and browser-selection tests to pass without live credentials.
- [x] Check the approved spec's eleven acceptance criteria against the finished tests and UI: provider-specific keys/models, Groq-only final-answer search, local deterministic actions, fallback success/failure, legacy preference migration, stale-response protection, and console compatibility.
- [x] Run `git diff --check`; expect no whitespace errors.
- [x] Review the final diff to confirm no keys, browser-held secrets, unrelated changes, or Gemini/DeepSeek search tools were introduced.
