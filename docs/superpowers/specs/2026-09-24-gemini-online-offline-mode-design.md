# Groq Online and Qwen Offline Mode

## Goal

Let each web UI user choose Groq Online mode or local Qwen Offline mode, with automatic Qwen fallback when Groq cannot serve a request.

## Approved understanding

- Online mode uses a Groq cloud model.
- Offline mode uses the existing local Qwen model.
- Users can select either mode in the web UI.
- If Groq reaches its usage limit or has a service failure, that request is handled by Qwen and the UI reflects the switch to Offline.
- The selected mode is held by the user's browser and sent with each command; it does not change the mode for other browser sessions.

## User experience

Add an Online/Offline dropdown to the chat header in `templates/index.html`. Initialize it to Online. Send the current mode with each `/command` request. If the backend falls back to Qwen, its response identifies the effective mode as Offline; the UI updates the dropdown and status indicator accordingly. If the user chooses Offline, future requests use Qwen directly. If Online is selected again, future requests try Groq again.

The existing chat response text remains visible as it is today. A Groq failure followed by successful local inference returns the local answer rather than a cloud error. If local inference also fails, return a clear failed-request response and keep the UI's mode aligned with the effective mode reported by the server.

## Architecture and data flow

1. The browser submits `{command, mode}` to Flask's existing `/command` route.
2. Flask validates the requested mode and calls the assistant with that mode.
3. Offline mode invokes the existing Qwen/Ollama path.
4. Online mode calls Groq through a server-side provider integration, using `GROQ_API_KEY` from the process environment. The key is never sent to the browser.
5. On Groq quota, network, or service errors, the assistant tries Qwen for that request.
6. Flask returns the normal message plus the effective mode (Online or Offline) so the browser can update its selector and status.

The assistant owns model selection and fallback. The web server owns request validation and response serialization. The browser owns the per-session selection and presentation. The current assistant console continues to work with its existing local Qwen behavior.

## Error handling and security

- Missing or invalid mode values are rejected with an appropriate client error; they must not silently invoke an unexpected provider.
- A missing `GROQ_API_KEY` produces an actionable configuration error for an Online request, then uses Qwen as the fallback.
- Groq quota, connectivity, and service errors trigger Qwen fallback.
- If both providers fail, the command endpoint returns an error instead of claiming success.
- Never log or return the API key. Keep it in an environment variable, not source files or frontend code.

## Scope

This change covers model selection for web chat requests, Groq integration, automatic Qwen fallback, and UI mode synchronization. It does not add cloud-model support to the console, persistent user accounts/preferences, or a Groq-generated response cache.

## Acceptance criteria

1. The web UI presents Online and Offline choices and defaults to Online.
2. Offline requests use the existing local Qwen model without calling Groq.
3. Online requests use Groq when configured and available.
4. Groq quota or service failures cause the same request to fall back to Qwen.
5. A successful fallback returns the Qwen answer and updates the browser to Offline.
6. Selecting Online again retries Groq on the next request.
7. The Groq key remains server-side and is loaded from `GROQ_API_KEY`.
8. The existing Flask command flow and console local-model flow remain usable.

## Verification expectations

During implementation, exercise Offline routing, Online routing, quota/service fallback, missing-key fallback, invalid mode handling, and UI mode synchronization. Use mocked provider calls for automated checks so verification does not consume Groq quota or require a live API key; perform a live Groq smoke check only when a key is configured.
