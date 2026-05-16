"""End-to-end test for the autonomous tool creator pipeline.

Scenario:
  1. A novel request arrives that no existing tool can handle.
  2. The server returns "I don't know how to do that yet…" immediately.
  3. A background task runs: generator → validator → installer.
  4. The new tool is registered in the ToolRegistry.
  5. A second identical request is routed to the new tool, which runs and
     returns a real response.

Generator is mocked to return a pre-written valid tool source (avoids
needing a real Ollama server). Validator and installer run for real so
the subprocess check and file-write path are exercised.
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.models import AssistantResponse, Transcript
from server.tools.base import ToolRegistry

# ---------------------------------------------------------------------------
# Pre-written tool that the validator subprocess will accept.
# Only uses server.tools.base (no external HTTP, no disallowed imports).
# ---------------------------------------------------------------------------

_TOOL_NAME = "air_quality_test"
_TOOL_SOURCE = """\
from server.tools.base import BaseTool

class AirQualityTool(BaseTool):
    name = "air_quality_test"
    description = "Returns air quality information for the local area."
    parameters = {"type": "object", "properties": {}, "required": []}

    async def run(self, params: dict, user: str) -> str:
        return "Air quality is Good (AQI 42)."
"""

_GENERATED_DIR = (
    Path(__file__).resolve().parents[1] / "server" / "tools" / "generated"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _transcript(text: str = "what's the air quality outside?") -> Transcript:
    return Transcript(session_id=str(uuid.uuid4()), text=text, user="owner")


def _mock_websocket() -> MagicMock:
    ws = MagicMock()
    ws.send_text = AsyncMock()
    return ws


# ---------------------------------------------------------------------------
# Fixture: clean up the test-generated tool file before and after.
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def cleanup_test_tool():
    tool_file = _GENERATED_DIR / f"{_TOOL_NAME}.py"
    tool_file.unlink(missing_ok=True)
    mod_key = f"server.tools.generated.{_TOOL_NAME}"
    sys.modules.pop(mod_key, None)
    yield
    tool_file.unlink(missing_ok=True)
    sys.modules.pop(mod_key, None)


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------


async def test_novel_request_creates_tool_and_works_on_second_request():
    """Full pipeline: novel intent → tool created → second request uses it."""
    registry = ToolRegistry()
    transcript = _transcript()
    ws = _mock_websocket()

    # Generator is mocked: returns our pre-written valid source instead of
    # calling the real Ollama model.
    mock_generator = MagicMock()
    mock_generator.generate = AsyncMock(return_value=_TOOL_SOURCE)

    # Router returns no tool + a response indicating unmet capability → heuristic triggers.
    mock_router_no_match = MagicMock()
    mock_router_no_match.route = AsyncMock(
        return_value=(None, "I don't have access to air quality data.")
    )

    # ------------------------------------------------------------------ #
    # First request: novel intent
    # ------------------------------------------------------------------ #
    with (
        patch("server.main._router", mock_router_no_match),
        patch("server.main._generator", mock_generator),
        patch("server.main._registry", registry),
    ):
        from server.main import _handle_transcript

        response1 = await _handle_transcript(transcript, ws)

        # Drain the event loop so the background _create_and_notify task
        # (spawned via asyncio.create_task) runs to completion inside the
        # active patch context.
        pending = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)

    # ------------------------------------------------------------------ #
    # Assertions on first response
    # ------------------------------------------------------------------ #
    assert response1 is not None
    assert "don't know how to do that yet" in response1.text
    assert "figure it out" in response1.text

    # ------------------------------------------------------------------ #
    # Tool must now be installed in the registry
    # ------------------------------------------------------------------ #
    tool = registry.get(_TOOL_NAME)
    assert tool is not None, (
        f"Expected tool '{_TOOL_NAME}' to be registered after background creation"
    )

    # The generated file must exist on disk.
    assert (_GENERATED_DIR / f"{_TOOL_NAME}.py").exists(), (
        "Tool source file was not written to server/tools/generated/"
    )

    # The completion notification ("I can do that now") must have been sent
    # over the WebSocket by _create_and_notify.
    ws.send_text.assert_called_once()
    sent_json = ws.send_text.call_args[0][0]
    completion = AssistantResponse.model_validate_json(sent_json)
    assert "I can do that now" in completion.text

    # ------------------------------------------------------------------ #
    # Second request: router routes to the newly installed tool
    # ------------------------------------------------------------------ #
    mock_router_with_tool = MagicMock()
    mock_router_with_tool.route = AsyncMock(
        return_value=(MagicMock(tool_name=_TOOL_NAME, params={}), "")
    )

    with (
        patch("server.main._router", mock_router_with_tool),
        patch("server.main._registry", registry),
    ):
        response2 = await _handle_transcript(transcript, ws)

    assert response2 is not None
    assert "Air quality" in response2.text
    assert "AQI" in response2.text
