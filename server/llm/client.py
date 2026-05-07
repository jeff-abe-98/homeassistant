from __future__ import annotations

from ollama import AsyncClient, Message

from shared.config import OllamaConfig


class OllamaClient:
    def __init__(self, cfg: OllamaConfig) -> None:
        self._model = cfg.model
        self._client = AsyncClient(host=cfg.host)

    async def chat(
        self,
        messages: list[dict[str, str]],
    ) -> str:
        """Send a messages list to Ollama and return the assistant reply text."""
        response = await self._client.chat(model=self._model, messages=messages)
        return response.message.content

    async def complete(self, system_prompt: str, user_message: str) -> str:
        """Convenience wrapper: build a two-message conversation and return the reply."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        return await self.chat(messages)

    async def chat_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
    ) -> Message:
        """Chat with function-calling schemas; returns the raw Message (may have .tool_calls)."""
        response = await self._client.chat(
            model=self._model,
            messages=messages,
            tools=tools,
        )
        return response.message
