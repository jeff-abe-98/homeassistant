"""HailoRT-backed LLM client — same interface as the old OllamaClient."""
from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from shared.config import HailoConfig

log = logging.getLogger(__name__)

# Lazy import — module still loads on machines without Hailo hardware (tests mock it).
try:
    from hailo_platform import VDevice as _VDevice
    from hailo_platform.genai import LLM as _HailoLLM

    _HAILO_AVAILABLE = True
except ImportError:
    _HAILO_AVAILABLE = False
    _VDevice = None  # type: ignore[assignment]
    _HailoLLM = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class LLMError(Exception):
    """Raised when an LLM request fails."""


class LLMTimeoutError(LLMError):
    """Raised when an LLM request exceeds the configured timeout."""


# ---------------------------------------------------------------------------
# Tool-call response types — mirror the Ollama Message interface so callers
# (ToolRouter) need no changes.
# ---------------------------------------------------------------------------


@dataclass
class ToolFunction:
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolCallItem:
    function: ToolFunction


@dataclass
class ToolMessage:
    content: str | None
    tool_calls: list[ToolCallItem] | None


# Qwen2 function-calling output format:
#   <tool_call>{"name": "...", "arguments": {...}}</tool_call>
_TOOL_CALL_RE = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.DOTALL)


def _parse_tool_call(text: str) -> ToolMessage:
    """Extract a tool call from raw LLM output, or return text as plain content."""
    m = _TOOL_CALL_RE.search(text)
    if m:
        try:
            data = json.loads(m.group(1))
            fn = ToolFunction(
                name=data.get("name", ""),
                arguments=data.get("arguments", {}),
            )
            return ToolMessage(content=None, tool_calls=[ToolCallItem(function=fn)])
        except json.JSONDecodeError:
            pass
    return ToolMessage(content=text.strip(), tool_calls=None)


def _tools_to_system_section(tools: list[dict]) -> str:
    """Render Ollama-format tool schemas into a system-prompt block for Qwen2."""
    if not tools:
        return ""
    lines = ["You have access to these tools:", ""]
    for t in tools:
        # Ollama format: {"type": "function", "function": {...}}
        fn = t.get("function", t)
        lines.append(f"Tool: {fn.get('name', '')}")
        lines.append(f"Description: {fn.get('description', '')}")
        props = fn.get("parameters", {}).get("properties", {})
        if props:
            lines.append("Parameters: " + ", ".join(props.keys()))
        lines.append("")
    lines += [
        'To use a tool output ONLY: <tool_call>{"name": "tool_name", "arguments": {...}}</tool_call>',
        "If no tool fits, respond in plain spoken language.",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class HailoLLMClient:
    """LLM client backed by hailo_platform.genai.LLM.

    The Hailo-10H NPU handles one inference task at a time; model is loaded
    once on first call and reused across all subsequent requests.
    """

    def __init__(self, cfg: HailoConfig, timeout: float = 30.0) -> None:
        if not _HAILO_AVAILABLE:
            raise ImportError(
                "hailo_platform is not installed. "
                "On Pi run: sudo apt install hailo-all hailo-genai"
            )
        self._cfg = cfg
        self._timeout = timeout
        self._vdevice: Any = None
        self._llm: Any = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_loaded(self) -> None:
        """Load model on first call (lazy init avoids blocking __init__)."""
        if self._llm is not None:
            return
        self._vdevice = _VDevice()
        self._llm = _HailoLLM(
            vdevice=self._vdevice,
            model=self._cfg.llm_model_path,
        )
        log.info("HailoLLMClient: loaded model from %s", self._cfg.llm_model_path)

    def _generate_sync(
        self,
        messages: list[dict],
        max_tokens: int = 200,
        temperature: float = 0.7,
    ) -> str:
        self._ensure_loaded()
        result = self._llm.generate(
            messages,
            max_generated_tokens=max_tokens,
            temperature=temperature,
        )
        # generate() may return str or a token iterator — normalise to str.
        if isinstance(result, str):
            return result
        return "".join(result)

    async def _generate(self, messages: list[dict], **kwargs: Any) -> str:
        loop = asyncio.get_event_loop()
        try:
            return await asyncio.wait_for(
                loop.run_in_executor(
                    None, lambda: self._generate_sync(messages, **kwargs)
                ),
                timeout=self._timeout,
            )
        except asyncio.TimeoutError as exc:
            raise LLMTimeoutError(
                f"LLM did not respond within {self._timeout}s"
            ) from exc
        except (LLMError, LLMTimeoutError):
            raise
        except Exception as exc:
            raise LLMError(f"LLM request failed: {exc}") from exc

    # ------------------------------------------------------------------
    # Public interface (matches old OllamaClient)
    # ------------------------------------------------------------------

    async def chat(self, messages: list[dict[str, str]]) -> str:
        """Send a messages list and return the assistant reply text."""
        return await self._generate(messages)

    async def complete(self, system_prompt: str, user_message: str) -> str:
        """Build a two-message conversation and return the reply."""
        return await self.chat([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ])

    async def chat_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
    ) -> ToolMessage:
        """Chat with function-calling schemas; returns ToolMessage.

        Tool schemas are injected into the system prompt because the Hailo
        Python API does not expose a native tools parameter.  The
        Qwen2-1.5B-Instruct-Function-Calling-v1 model outputs
        <tool_call>{...}</tool_call> which _parse_tool_call decodes.
        """
        tool_section = _tools_to_system_section(tools)
        augmented = list(messages)
        if augmented and augmented[0]["role"] == "system":
            augmented[0] = {
                "role": "system",
                "content": augmented[0]["content"] + "\n\n" + tool_section,
            }
        else:
            augmented.insert(0, {"role": "system", "content": tool_section})

        raw = await self._generate(augmented)
        return _parse_tool_call(raw)

    def close(self) -> None:
        """Release Hailo hardware resources."""
        if self._llm is not None:
            try:
                self._llm.release()
            except Exception:
                pass
        if self._vdevice is not None:
            try:
                self._vdevice.release()
            except Exception:
                pass
        self._llm = None
        self._vdevice = None
