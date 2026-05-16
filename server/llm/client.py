from __future__ import annotations

import asyncio

from ollama import AsyncClient, Message

from shared.config import OllamaConfig


class LLMError(Exception):
    """Raised when an LLM request fails."""


class LLMTimeoutError(LLMError):
    """Raised when an LLM request exceeds the configured timeout."""


class OllamaClient:
    def __init__(self, cfg: OllamaConfig) -> None:
        self._model = cfg.model
        self._timeout = cfg.timeout
        self._client = AsyncClient(host=cfg.host)

    async def chat(
        self,
        messages: list[dict[str, str]],
    ) -> str:
        """Send a messages list to Ollama and return the assistant reply text."""
        try:
            response = await asyncio.wait_for(
                self._client.chat(model=self._model, messages=messages),
                timeout=self._timeout,
            )
            return response.message.content
        except asyncio.TimeoutError as exc:
            raise LLMTimeoutError(
                f"LLM did not respond within {self._timeout}s"
            ) from exc
        except (LLMError, LLMTimeoutError):
            raise
        except Exception as exc:
            raise LLMError(f"LLM request failed: {exc}") from exc

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
        try:
            response = await asyncio.wait_for(
                self._client.chat(
                    model=self._model,
                    messages=messages,
                    tools=tools,
                ),
                timeout=self._timeout,
            )
            return response.message
        except asyncio.TimeoutError as exc:
            raise LLMTimeoutError(
                f"LLM did not respond within {self._timeout}s"
            ) from exc
        except (LLMError, LLMTimeoutError):
            raise
        except Exception as exc:
            raise LLMError(f"LLM request failed: {exc}") from exc
