# Hailo GenAI Python API — Research Notes

**Researched:** 2026-06-15  
**Hardware target:** Hailo-10H (AI HAT+ 2, 40 TOPS)

---

## Two Runtime Approaches

### A — Direct Python API (`hailo_platform.genai`) ← Chosen
Installed as part of the `hailo-genai` apt package alongside `hailo-all`.

```python
from hailo_platform import VDevice
from hailo_platform.genai import LLM
from hailo_apps.python.gen_ai_apps.gen_ai_utils import (
    llm_utils,
    streaming,
    message_formatter,
)
```

Workflow:
```python
vdevice = VDevice()
llm = LLM(vdevice=vdevice, model="/path/to/model.hef")

messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user",   "content": "What is the weather today?"},
]

# Blocking generation
response = llm.generate(messages, max_generated_tokens=200, temperature=0.7)

# Streaming generation (yields text chunks)
for chunk in streaming.generate_and_stream_response(
    llm=llm,
    prompt=messages,
    max_tokens=200,
):
    print(chunk, end="", flush=True)
```

Context management methods on `LLM`:
- `llm.save_context()` — snapshot KV-cache for conversation continuity
- `llm.load_context()` — restore snapshot
- `llm.clear_context()` — reset to zero

Tool parsing helpers (from `gen_ai_utils`):
- `tool_parsing.parse_function_call(response_text)` — extracts tool name + args from LLM output
- `tool_execution.execute_tool_call(...)` — dispatches to registered tool

### B — Ollama-compatible REST API (`hailo-ollama`)
Installed via apt as part of `hailo-gen-ai-model-zoo`. Exposes a server on port 8000.

```bash
hailo-ollama serve          # starts server at localhost:8000
hailo-ollama pull qwen2.5-instruct:1.5b
```

API is fully Ollama-compatible — identical to `http://localhost:11434` endpoints but at `:8000`.
Real-world projects (e.g., `be-more-hailo`) use `OLLAMA_HOST=0.0.0.0:8000` with `hailo-ollama serve`.

**We use Approach A** (direct Python API) because:
- No background server process needed
- Model path comes from our config (no pull/download step)
- Cleaner mock surface for unit tests

---

## Available Compiled Models (Hailo-10H)

| Model | Size | Notes |
|-------|------|-------|
| `Qwen2-1.5B-Instruct-Function-Calling-v1` | 1.5B | **Best for tool routing** — explicit function calling |
| `Qwen3-1.7B-Instruct` | 1.7B | Best reasoning; good conversational fallback |
| `Llama3.2-1B-Instruct` | 1B | Lightweight; fastest |
| `Qwen2.5-1.5B-Instruct` | 1.5B | General instruction following |
| `Qwen2-1.5B-Instruct` | 1.5B | Base instruct |
| `Qwen2.5-Coder-1.5B-Instruct` | 1.5B | Code-focused; not relevant here |
| `DeepSeek-R1-Distill-Qwen-1.5B` | 1.5B | Reasoning-distilled |

> **Note:** No 3B model is available for Hailo-10H. The plan.md reference to "Llama 3.2 3B" is incorrect — the largest available model is 1.7B.

**Recommendation for this project:**
- Tool routing: `Qwen2-1.5B-Instruct-Function-Calling-v1` — explicit function calling JSON output
- Conversational fallback: same model, or `Qwen3-1.7B-Instruct` if latency allows

---

## `HailoLLMClient` Design

Expose the same interface as the old `OllamaClient`:

```python
class HailoLLMClient:
    async def complete(self, system: str, user: str) -> str: ...
    async def chat(self, messages: list[dict]) -> str: ...
    async def chat_with_tools(self, messages: list[dict], tools: list[dict]) -> dict: ...
```

Since `LLM.generate()` is synchronous (blocking), wrap in `asyncio.get_event_loop().run_in_executor(None, ...)` to keep the async interface non-blocking.

When `hailo_platform` is not importable (CI / no hardware), raise `ImportError` with a clear message — the mock in tests patches at the class level.

---

## Streaming

`streaming.generate_and_stream_response()` yields str chunks. For our use case (voice TTS), we accumulate the full response rather than streaming word-by-word. This simplifies the interface.

---

## Installation Path (on Pi)

```bash
sudo apt install hailo-all hailo-genai hailo-gen-ai-model-zoo
# hailo_platform and hailo_platform.genai are installed as system Python packages
# Models (.hef files) downloaded to /usr/share/hailo/models/ or custom path
```

Download a model:
```bash
hailo-download-resources --group llm_chat --arch hailo10h
```

---

## Sources

- [hailo-ai/hailo-apps GenAI README](https://github.com/hailo-ai/hailo-apps/blob/main/hailo_apps/python/gen_ai_apps/README.md)
- [hailo-ai/hailo-apps simple_llm_chat](https://github.com/hailo-ai/hailo-apps/tree/main/hailo_apps/python/gen_ai_apps/simple_llm_chat)
- [hailo-ai/hailo_model_zoo_genai](https://github.com/hailo-ai/hailo_model_zoo_genai)
- [Hailo GenAI model explorer](https://hailo.ai/products/hailo-software/model-explorer/generative-ai/type/llm/)
- [moorew/be-more-hailo — real-world Hailo LLM agent](https://github.com/moorew/be-more-hailo/)
- [Bringing GenAI to the Edge — Hailo blog](https://hailo.ai/blog/bringing-generative-ai-to-the-edge-llm-on-hailo-10h/)
- [DeepWiki hailo-apps-infra GenAI](https://deepwiki.com/hailo-ai/hailo-apps-infra/6-genai-applications)
