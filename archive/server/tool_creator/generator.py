"""LLM-driven BaseTool code generator for the autonomous tool creator."""

from __future__ import annotations

import ast
import re
import textwrap

import shared.config as cfg_module
from server.llm.client import OllamaClient

_MAX_RETRIES = 3

_SYSTEM_PROMPT = textwrap.dedent("""\
    You are a Python code generator for a home assistant system.
    Generate a single Python module implementing a new tool subclass.

    Every tool must subclass BaseTool and follow this exact interface:

        from server.tools.base import BaseTool

        class MyTool(BaseTool):
            name = "tool_name"            # snake_case, unique identifier
            description = "..."           # one sentence; used by LLM to decide when to call
            parameters = {                # JSON Schema for the tool's arguments
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "..."
                    }
                },
                "required": ["query"]
            }

            async def run(self, params: dict, user: str) -> str:
                ...  # return a natural-language response string

    Rules:
    - Only import from the Python standard library or these packages:
      httpx, pydantic, yaml, json, asyncio, datetime, re, math, os, pathlib,
      shared.config, server.llm.client, server.tools.base
    - Use httpx.AsyncClient for any HTTP requests
    - Never use subprocess, eval, exec, or open() for writing files
    - The run() method must be async and always return a str
    - Output ONLY the Python source code — no explanations, no markdown fences
""")


class ToolGenerator:
    """Generates a new BaseTool implementation from a natural-language intent."""

    def __init__(self, llm: OllamaClient | None = None) -> None:
        self._llm = llm

    def _llm_client(self) -> OllamaClient:
        if self._llm is None:
            cfg = cfg_module.load()
            self._llm = OllamaClient(cfg.ollama)
        return self._llm

    async def generate(self, intent: str, existing_tool_names: list[str] | None = None) -> str:
        """Generate Python source for a new BaseTool from *intent*.

        Returns the source code string.  Raises ValueError if the LLM fails to
        produce valid Python after _MAX_RETRIES attempts.
        """
        existing = existing_tool_names or []
        user_message = _build_user_message(intent, existing)

        last_error: str = ""
        for attempt in range(1, _MAX_RETRIES + 1):
            retry_note = (
                f"\n\nPrevious attempt produced invalid Python: {last_error}. Fix it."
                if attempt > 1
                else ""
            )
            source = await self._llm_client().complete(
                _SYSTEM_PROMPT, user_message + retry_note
            )
            source = _strip_fences(source)
            error = _syntax_check(source)
            if error is None:
                return source
            last_error = error

        raise ValueError(
            f"LLM failed to generate valid Python after {_MAX_RETRIES} attempts. "
            f"Last error: {last_error}"
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_user_message(intent: str, existing_tool_names: list[str]) -> str:
    parts = [f"Create a new tool that does the following:\n\n{intent}"]
    if existing_tool_names:
        names = ", ".join(existing_tool_names)
        parts.append(f"\nDo not reuse any of these existing tool names: {names}")
    return "\n".join(parts)


def _strip_fences(text: str) -> str:
    """Remove markdown code fences if present."""
    text = text.strip()
    # Match ```python ... ``` or ``` ... ```
    m = re.search(r"```(?:python)?\n?(.*?)```", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return text


def _syntax_check(source: str) -> str | None:
    """Return an error message if *source* is not valid Python, else None."""
    try:
        ast.parse(source)
        return None
    except SyntaxError as exc:
        return str(exc)
