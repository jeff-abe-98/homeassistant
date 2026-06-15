"""System-prompt construction for the Pi LLM (small model, ~1.5B params)."""
from __future__ import annotations

from pathlib import Path

_BASE = """\
You are a helpful home assistant for a household in Chicago, IL.
Your responses are read aloud by a text-to-speech system.
Write entirely in plain spoken language — no bullet points, markdown, headers, or symbols.
Be concise: one to three sentences unless the user asks for more.

You can help with: weather, CTA Blue Line trains, Google Calendar events, to-do lists, \
Spotify music, and TV control.\
"""

_KNOWN_USER = "You are speaking with {name}. Address them by name naturally when appropriate."
_UNKNOWN_USER = (
    "You do not know the speaker's voice. "
    "If they ask for something personal, politely ask who they are."
)

# Path where AI-generated tools store their _instructions.md files.
_GENERATED_TOOLS_DIR = Path(__file__).parent.parent.parent / "tools" / "generated"


def _load_tool_instructions() -> str:
    """Collect _instructions.md files from all generated tools."""
    if not _GENERATED_TOOLS_DIR.exists():
        return ""
    parts: list[str] = []
    for md in sorted(_GENERATED_TOOLS_DIR.glob("*_instructions.md")):
        try:
            parts.append(md.read_text().strip())
        except OSError:
            pass
    return "\n\n".join(parts)


def build_system_prompt(
    user: str = "unknown",
    context_turns: list[dict] | None = None,
    tool_instructions: str | None = None,
) -> str:
    """Build the system prompt for the Hailo LLM.

    Args:
        user: Speaker name ("owner", "emily") or "unknown".
        context_turns: Recent conversation turns already injected separately
                       into the messages list — only used here to mention
                       memory when present.
        tool_instructions: Optional override for generated-tool instructions;
                           if None, reads from tools/generated/*_instructions.md.
    """
    if user and user not in ("unknown", ""):
        user_line = _KNOWN_USER.format(name=user.capitalize())
    else:
        user_line = _UNKNOWN_USER

    extra_tools = tool_instructions if tool_instructions is not None else _load_tool_instructions()

    parts = [_BASE, user_line]

    if context_turns:
        parts.append(
            "You have access to the recent conversation above. "
            "Use it for context but do not re-read it aloud."
        )

    if extra_tools:
        parts.append("Additional tool guidance:\n" + extra_tools)

    return "\n\n".join(parts)
