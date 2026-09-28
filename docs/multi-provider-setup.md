# Configure Jarvis model providers

The web chat lets you select Groq, DeepSeek, Gemini, or Local Qwen. Cloud keys are read by the Jarvis server only; they are never sent to the browser.

## 1. Install Python dependencies

From the project folder, run:

```powershell
python -m pip install -r requirements.txt
```

## 2. Set a cloud provider key

In the same PowerShell window that you use to start Jarvis, set the key for the provider you want. Replace the placeholder with the key from that provider's developer console:

```powershell
$env:GROQ_API_KEY = "your-groq-key"
$env:DEEPSEEK_API_KEY = "your-deepseek-key"
$env:GEMINI_API_KEY = "your-gemini-key"
```

Set only the key or keys you plan to use. These commands apply to that PowerShell window and its child processes. Start Jarvis from the same window:

```powershell
python web_server.py
```

Do not put real keys in Python, HTML, JavaScript, or a committed file. If you close PowerShell, set the variables again before restarting the server.

## 3. Optional model names

Jarvis has defaults for each cloud service. To choose another model supported by the provider, set its model variable before starting the server:

```powershell
$env:GROQ_MODEL = "openai/gpt-oss-120b"
$env:DEEPSEEK_MODEL = "deepseek-flash"
$env:GEMINI_MODEL = "gemini-3.8-flash"
```

## 4. Use Local Qwen

Install and start Ollama, then download the configured local model:

```powershell
ollama pull qwen2.5:7b-instruct-q3_K_M
```

Choose **Local Qwen** in the web selector. The console continues to use local Qwen by default.

## Provider behavior

- The selector choice is used for intent parsing and the final conversational answer.
- If a selected cloud provider is not configured or its request fails, Jarvis retries the request with Local Qwen and changes the selector to Local Qwen after a successful fallback.
- Jarvis does not switch from one cloud provider to another.
- Automatic browser search is enabled only for Groq final conversational answers. Intent parsing, DeepSeek, and Gemini do not receive a search tool.
