"""LLM function-calling router: selects a tool and extracts its params from a transcript."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from server.llm.client import OllamaClient
from server.llm.prompts import build_system_prompt
from server.tools.base import ToolRegistry
from shared.models import Transcript


@dataclass
class ToolCall:
    tool_name: str
    params: dict[str, Any] = field(default_factory=dict)


class ToolRouter:
    """Routes a Transcript to a registered tool using Ollama function calling.

    Returns (ToolCall, fallback_text) in a single LLM call:
    - Tool selected: (ToolCall, "")
    - No tool: (None, llm_response_text) — reuse the LLM's reply directly.
    """

    def __init__(self, llm: OllamaClient, registry: ToolRegistry) -> None:
        self._llm = llm
        self._registry = registry

    async def route(self, transcript: Transcript) -> tuple[ToolCall | None, str]:
        """Ask the LLM to select a tool or respond conversationally.

        Returns (tool_call, fallback_text).  Exactly one branch is meaningful:
        tool_call is not None when a registered tool was selected;
        fallback_text is non-empty when the LLM responded directly (no tool).
        """
        schemas = self._registry.function_schemas()
        if not schemas:
            # No tools registered — plain chat, return response as fallback.
            content = await self._llm.complete(
                build_system_prompt(transcript.user), transcript.text
            )
            return None, content

        messages = [
            {"role": "system", "content": build_system_prompt(transcript.user)},
            {"role": "user", "content": transcript.text},
        ]

        message = await self._llm.chat_with_tools(messages, schemas)

        if message.tool_calls:
            first = message.tool_calls[0]
            return ToolCall(
                tool_name=first.function.name,
                params=dict(first.function.arguments),
            ), ""

        # LLM responded conversationally — return its text as fallback.
        return None, message.content or ""
