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

    Returns a ToolCall when the LLM picks a tool, or None when the request is
    conversational and should fall through to a plain chat completion.
    """

    def __init__(self, llm: OllamaClient, registry: ToolRegistry) -> None:
        self._llm = llm
        self._registry = registry

    async def route(self, transcript: Transcript) -> ToolCall | None:
        """Ask the LLM to select a tool and extract parameters.

        Returns None if no tools are registered or the LLM determines no tool
        is needed for this request.
        """
        schemas = self._registry.function_schemas()
        if not schemas:
            return None

        messages = [
            {"role": "system", "content": build_system_prompt(transcript.user)},
            {"role": "user", "content": transcript.text},
        ]

        message = await self._llm.chat_with_tools(messages, schemas)

        if not message.tool_calls:
            return None

        first = message.tool_calls[0]
        return ToolCall(
            tool_name=first.function.name,
            params=dict(first.function.arguments),
        )
