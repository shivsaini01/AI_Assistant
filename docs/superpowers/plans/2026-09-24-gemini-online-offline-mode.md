# Groq Online and Qwen Offline Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a web UI mode selector for Groq Online and local Qwen Offline, with automatic Qwen fallback when Groq is unavailable.

**Architecture:** Add a Groq provider module using the `groq` SDK, and route assistant conversation responses by requested mode while retaining Qwen as the console default. The web endpoint validates and forwards mode, returning both the message and effective mode; the browser persists the selection for its tab and adopts Offline when the server falls back.

**Tech Stack:** Python, Flask, Ollama, Groq Python SDK, browser JavaScript and CSS.

**Spec:** [2026-09-24-gemini-online-offline-mode-design.md](../specs/2026-09-24-gemini-online-offline-mode-design.md)

## Global Constraints

- Keep `GROQ_API_KEY` server-side in the process environment.
- Online requests use Groq; Offline requests use the existing local Qwen/Ollama model.
- Groq quota, connectivity, service, or configuration failures fall back to Qwen for the current request.
- The web selection is per browser tab and is sent on every `/command` request.
- Preserve the existing `process_user_input(user_text)` console behavior.
- Do not add or run tests unless the user asks for implementation verification.
- Use the official Groq Python SDK: [Groq quickstart](https://console.groq.com/docs/quickstart).

## Review Focus

- Missing `GROQ_API_KEY`: Online mode should fall back to Qwen and the UI should reflect Offline.
- Invalid/missing request mode: the endpoint should reject the request with HTTP 400.
- Groq returns no text: treat this as a provider failure and use Qwen.
- Qwen also fails after Groq failure: return an error response without claiming a successful answer.
- User changes mode while a request is in flight: keep the submitted request's effective mode from overwriting a newer user selection.

## File Map

- Create `ai_providers.py`: encapsulate Groq client setup and text generation, including server-side key/model configuration.
- Modify `assistant.py`: reuse its existing system prompt and conversation context for Groq, route web conversation responses by requested mode, fall back to Qwen, and expose the effective mode to the web caller without changing console output behavior.
- Modify `web_server.py`: validate mode and return `{success, message, mode}` from `/command`.
- Modify `templates/index.html`: add the Online/Offline dropdown and mode status, send mode with each request, retain the tab selection, and synchronize it after fallback.
- Modify `requirements.txt` only if one exists or is added as the repository's dependency manifest; add `groq` there. If no manifest exists, add a minimal `requirements.txt` covering currently imported runtime packages plus `groq` only after inspecting imports during execution.

### Task 1: Add the Groq provider and dependency declaration

**Files:**
- Create: `ai_providers.py`
- Create or modify: `requirements.txt`

**Interfaces:**
- Produces: `generate_groq_text(system_prompt: str, user_text: str) -> str`.
- Reads `GROQ_API_KEY`; reads optional `GROQ_MODEL`, defaulting to `openai/gpt-oss-120b`.
- Raises provider/configuration errors to the assistant routing layer; never returns an empty response as a success.

- [ ] Inspect existing imports and repository setup to determine the minimum safe dependency manifest; declare `groq` and avoid replacing existing dependency pins.
- [ ] Implement a small Groq adapter that creates a server-side client, passes system instructions and user text, and returns non-empty response text.
- [ ] Keep credentials out of source, frontend code, and logs; make absent configuration distinguishable to the fallback layer.
- [ ] Review the adapter and dependency diff for accidental secret exposure or unrelated dependency changes.

### Task 2: Route assistant conversations by mode and report fallback

**Files:**
- Modify: `assistant.py`
- Consume: `ai_providers.generate_groq_text(system_prompt, user_text)`

**Interfaces:**
- Preserve: `process_user_input(user_text)` returns a string and continues to use Qwen for console conversations.
- Add a web-capable path: `process_user_input(user_text, mode="offline", include_mode=False)` returns a string by default; when `include_mode=True`, returns `(message, effective_mode)`.
- Add `ask_ai_with_mode(user_text, conversation_context, requested_mode) -> (message, effective_mode)` for web requests; keep `ask_ai(user_text, conversation_context="") -> str` as the console-compatible local wrapper.

- [ ] Extract the existing system prompt construction and local Ollama invocation so both provider paths receive the same Jarvis instructions and recent conversation context.
- [ ] Add `ask_ai_with_mode` for web natural language requests: Online routes through Groq; Offline routes through Ollama.
- [ ] On Groq configuration, quota, network, service, or empty-response failures, invoke the existing Qwen call for that same request and mark effective mode Offline.
- [ ] Let the shared Ollama call raise provider errors; if Qwen fails after Gemini fails (or fails in Offline mode), propagate the error to Flask rather than storing or returning a success claim. Keep the `ask_ai` console wrapper's existing human-readable error string behavior.
- [ ] Keep command execution paths (file search, app launch, skills, etc.) unchanged; report the selected mode as effective when no language model is needed.
- [ ] Preserve existing console calls and string return values.
- [ ] Review every `process_user_input` return path to ensure web requests consistently include the effective mode and console callers retain prior behavior.

### Task 3: Extend the Flask request and response contract

**Files:**
- Modify: `web_server.py`
- Consume: `process_user_input(user_text, mode=..., include_mode=True)`

**Interfaces:**
- Request: JSON object with `command` and required `mode` (`online` or `offline`).
- Success response: `{"success": true, "message": "...", "mode": "online|offline"}`.
- Invalid mode response: HTTP 400 with a clear message.

- [ ] Validate that `mode` is present, is a string, and normalizes to `online` or `offline`; reject missing or invalid mode with HTTP 400. The browser supplies Online by default, and the Python console continues defaulting to local mode.
- [ ] Call the web-capable assistant path and serialize both its message and effective mode.
- [ ] Preserve existing empty-body, empty-command, and exception handling behavior, ensuring provider failure is surfaced as an error response.
- [ ] Review response branches so each successful response contains a valid mode and errors do not claim success.

### Task 4: Add mode selection and fallback synchronization to the web UI

**Files:**
- Modify: `templates/index.html`
- Consume: `/command` mode request/response contract from Task 3.

**Interfaces:**
- Selection values: `online` and `offline`.
- Browser storage: a dedicated `sessionStorage` key for current mode, defaulting to Online.
- Mode indicator: displays the effective selected mode.

- [ ] Replace the hardcoded Online status with an accessible dropdown for Online and Offline and a status indicator styled consistently with the existing header.
- [ ] Initialize mode from the dedicated `sessionStorage` key, defaulting to Online, and save manual selection changes.
- [ ] Include the selected mode in every `/command` JSON body.
- [ ] On a successful response, update and persist the selector only if its current value still matches the mode submitted for that request; this avoids overwriting a newer manual choice.
- [ ] When the server reports a fallback mode, update the visible selector and status to Offline for subsequent requests.
- [ ] Keep existing chat rendering, error display, send behavior, and responsive layout intact.
- [ ] Review keyboard accessibility, narrow-screen layout, and request/response field names against the Flask contract.

### Task 5: Review the completed change

**Files:**
- Review: `ai_providers.py`, `assistant.py`, `web_server.py`, `templates/index.html`, and dependency manifest.

- [ ] Check that all spec acceptance criteria map to the implementation and that mode reporting is consistent across success, fallback, and error paths.
- [ ] Inspect the final diff for unrelated edits and verify no API key was added to tracked files.
- [ ] Do not add or run tests unless the user requests verification.
