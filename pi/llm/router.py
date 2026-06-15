"""LLM function-calling router — selects a tool and extracts params from a transcript."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from pi.llm.hailo_client import HailoLLMClient
from pi.llm.prompts import build_system_prompt
from shared.models import Transcript


@dataclass
class ToolCall:
    tool_name: str
    params: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class ToolRegistryLike(Protocol):
    """Minimal interface ToolRouter requires from a registry."""

    def function_schemas(self) -> list[dict]: ...


class ToolRouter:
    """Routes a Transcript to a registered tool using Hailo function calling.

    Returns (ToolCall | None, str) in a single LLM call:
    - Tool selected  → (ToolCall, "")
    - No tool match  → (None, llm_response_text)  — reuse the LLM reply directly.
    """

    def __init__(self, llm: HailoLLMClient, registry: ToolRegistryLike) -> None:
        self._llm = llm
        self._registry = registry

    async def route(
        self,
        transcript: Transcript,
        context_turns: list[dict] | None = None,
    ) -> tuple[ToolCall | None, str]:
        """Ask the LLM to select a tool or respond conversationally.

        Args:
            transcript: The recognised speech, with .text and .user.
            context_turns: Recent conversation turns from session memory
                           (each dict has "role" and "content").

        Returns:
            (tool_call, fallback_text) — exactly one branch is meaningful.
        """
        schemas = self._registry.function_schemas()
        system = build_system_prompt(
            user=transcript.user,
            context_turns=context_turns or [],
        )

        if not schemas:
            content = await self._llm.complete(system, transcript.text)
            return None, content

        messages: list[dict] = [{"role": "system", "content": system}]
        if context_turns:
            messages.extend(context_turns)
        messages.append({"role": "user", "content": transcript.text})

        message = await self._llm.chat_with_tools(messages, schemas)

        if message.tool_calls:
            first = message.tool_calls[0]
            return ToolCall(
                tool_name=first.function.name,
                params=dict(first.function.arguments),
            ), ""

        return None, message.content or ""
