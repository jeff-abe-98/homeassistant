from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable, Coroutine
from typing import Any

import websockets

from shared.config import AppConfig
from shared.models import AssistantResponse, AudioChunk, Transcript

logger = logging.getLogger(__name__)

OnTranscript = Callable[[Transcript], Coroutine[Any, Any, None]]
OnResponse = Callable[[AssistantResponse], Coroutine[Any, Any, None]]


class AssistantClient:
    """WebSocket client for the server /ws endpoint.

    Protocol (per utterance):
      1. send_audio_chunk() for each frame; final chunk has is_final=True
      2. receive_transcript(session_id) → Transcript from STT
      3. send_transcript(transcript) to trigger LLM
      4. receive_response(session_id) → AssistantResponse from LLM
    """

    def __init__(
        self,
        config: AppConfig,
        on_transcript: OnTranscript | None = None,
        on_response: OnResponse | None = None,
    ) -> None:
        # server.host is the server's bind address; Pi connects to its LAN IP.
        # Set server.host to the server's actual LAN IP in config/settings.yaml.
        host = config.server.host
        self._url = f"ws://{host}:{config.server.port}/ws"
        self._on_transcript = on_transcript
        self._on_response = on_response
        self._ws: websockets.WebSocketClientProtocol | None = None
        self._listener: asyncio.Task[None] | None = None
        self._queues: dict[str, asyncio.Queue[dict[str, Any]]] = {}

    async def connect(self) -> None:
        self._ws = await websockets.connect(self._url)
        self._listener = asyncio.create_task(self._listen())
        logger.info("Connected to %s", self._url)

    async def disconnect(self) -> None:
        if self._listener and not self._listener.done():
            self._listener.cancel()
            try:
                await self._listener
            except asyncio.CancelledError:
                pass
        if self._ws:
            await self._ws.close()
            self._ws = None
        logger.info("Disconnected from server")

    async def __aenter__(self) -> AssistantClient:
        await self.connect()
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.disconnect()

    async def send_audio_chunk(self, chunk: AudioChunk) -> None:
        if self._ws is None:
            raise RuntimeError("Not connected")
        await self._ws.send(chunk.model_dump_json())

    async def send_transcript(self, transcript: Transcript) -> None:
        if self._ws is None:
            raise RuntimeError("Not connected")
        await self._ws.send(transcript.model_dump_json())

    async def receive_transcript(self, session_id: str) -> Transcript:
        """Wait for the server's STT result for this session."""
        msg = await self._queue_for(session_id).get()
        transcript = Transcript.model_validate(msg)
        if self._on_transcript:
            await self._on_transcript(transcript)
        return transcript

    async def receive_response(self, session_id: str) -> AssistantResponse:
        """Wait for the server's LLM response for this session."""
        msg = await self._queue_for(session_id).get()
        response = AssistantResponse.model_validate(msg)
        if self._on_response:
            await self._on_response(response)
        self._queues.pop(session_id, None)
        return response

    def _queue_for(self, session_id: str) -> asyncio.Queue[dict[str, Any]]:
        if session_id not in self._queues:
            self._queues[session_id] = asyncio.Queue()
        return self._queues[session_id]

    async def _listen(self) -> None:
        try:
            async for raw in self._ws:  # type: ignore[union-attr]
                try:
                    msg = json.loads(raw)
                    session_id = msg.get("session_id")
                    if session_id:
                        await self._queue_for(session_id).put(msg)
                    else:
                        logger.warning("Server message missing session_id: %s", msg)
                except json.JSONDecodeError as exc:
                    logger.warning("Bad JSON from server: %s", exc)
        except (websockets.ConnectionClosed, asyncio.CancelledError):
            pass
        except Exception as exc:
            logger.error("Listener crashed: %s", exc, exc_info=True)
