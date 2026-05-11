"""Google Tasks tools — add item, list incomplete items, complete item by name."""

from __future__ import annotations

import shared.config as cfg_module
from server.llm.client import OllamaClient
from server.tools.base import BaseTool
from server.tools.google_auth import build_service, is_configured


def _default_tasklist_id(service) -> str | None:
    """Return the ID of the first task list, or None on failure."""
    try:
        result = service.tasklists().list(maxResults=10).execute()
        items = result.get("items", [])
        return items[0]["id"] if items else None
    except Exception:
        return None


def _find_task_by_title(service, tasklist_id: str, title: str) -> dict | None:
    """Return the first incomplete task whose title matches (case-insensitive)."""
    try:
        result = (
            service.tasks()
            .list(tasklist=tasklist_id, showCompleted=False, maxResults=100)
            .execute()
        )
    except Exception:
        return None
    needle = title.strip().lower()
    for task in result.get("items", []):
        if task.get("title", "").lower() == needle:
            return task
    return None


class AddTaskTool(BaseTool):
    name = "add_task"
    description = (
        "Add an item to the user's Google Tasks list. Use for requests like "
        "'add oat milk to my list', 'put eggs on my shopping list', "
        "'remind me to call the dentist', 'add a to-do for laundry'."
    )
    parameters = {
        "type": "object",
        "properties": {
            "item": {
                "type": "string",
                "description": "The task or item to add.",
            },
        },
        "required": ["item"],
    }

    def __init__(self) -> None:
        self._llm: OllamaClient | None = None

    def _llm_client(self) -> OllamaClient:
        if self._llm is None:
            cfg = cfg_module.load()
            self._llm = OllamaClient(cfg.ollama)
        return self._llm

    async def run(self, params: dict, user: str) -> str:
        if not is_configured():
            return (
                "Google Tasks isn't set up yet — I need OAuth2 credentials. "
                "Check config/google_credentials.json for setup instructions."
            )

        service = build_service("tasks", "v1")
        if service is None:
            return "I couldn't connect to Google Tasks right now."

        item = params.get("item", "").strip()
        if not item:
            return "I need an item name to add it to your list."

        tasklist_id = _default_tasklist_id(service)
        if tasklist_id is None:
            return "I couldn't find a task list to add that to."

        try:
            service.tasks().insert(tasklist=tasklist_id, body={"title": item}).execute()
        except Exception as exc:
            return f"I had trouble adding that to your list: {exc}"

        return f"Done — I've added '{item}' to your list."


class ListTasksTool(BaseTool):
    name = "list_tasks"
    description = (
        "Read back incomplete items from the user's Google Tasks list. "
        "Use for requests like 'what's on my list', 'what do I need to pick up', "
        "'read me my to-do list', 'what are my tasks'."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The user's task list question verbatim.",
            },
        },
        "required": ["query"],
    }

    def __init__(self) -> None:
        self._llm: OllamaClient | None = None

    def _llm_client(self) -> OllamaClient:
        if self._llm is None:
            cfg = cfg_module.load()
            self._llm = OllamaClient(cfg.ollama)
        return self._llm

    async def run(self, params: dict, user: str) -> str:
        if not is_configured():
            return (
                "Google Tasks isn't set up yet — I need OAuth2 credentials. "
                "Check config/google_credentials.json for setup instructions."
            )

        service = build_service("tasks", "v1")
        if service is None:
            return "I couldn't connect to Google Tasks right now."

        tasklist_id = _default_tasklist_id(service)
        if tasklist_id is None:
            return "I couldn't find a task list to read."

        try:
            result = (
                service.tasks()
                .list(tasklist=tasklist_id, showCompleted=False, maxResults=100)
                .execute()
            )
        except Exception as exc:
            return f"I had trouble reading your list: {exc}"

        items = result.get("items", [])
        if not items:
            return "Your list is empty — nothing to do."

        titles = [t.get("title", "(no title)") for t in items]
        tasks_text = "\n".join(f"- {t}" for t in titles)

        user_hint = (
            f" You are speaking with {user.title()}."
            if user and user.lower() != "unknown"
            else ""
        )
        system = (
            "You are a home assistant. Read back the following to-do list items naturally "
            "in plain spoken English. Be concise.{hint}".format(hint=user_hint)
        )
        user_msg = (
            f"Question: {params.get('query', 'what is on my list')}\n\n"
            f"Tasks:\n{tasks_text}"
        )
        return await self._llm_client().complete(system, user_msg)


class CompleteTaskTool(BaseTool):
    name = "complete_task"
    description = (
        "Mark a task as done in the user's Google Tasks list. Use for requests like "
        "'mark oat milk as done', 'I got the eggs', 'check off laundry', "
        "'complete the dentist task', 'cross off bread'."
    )
    parameters = {
        "type": "object",
        "properties": {
            "item": {
                "type": "string",
                "description": "The name of the task to mark as complete.",
            },
        },
        "required": ["item"],
    }

    async def run(self, params: dict, user: str) -> str:
        if not is_configured():
            return (
                "Google Tasks isn't set up yet — I need OAuth2 credentials. "
                "Check config/google_credentials.json for setup instructions."
            )

        service = build_service("tasks", "v1")
        if service is None:
            return "I couldn't connect to Google Tasks right now."

        item = params.get("item", "").strip()
        if not item:
            return "I need an item name to mark it as done."

        tasklist_id = _default_tasklist_id(service)
        if tasklist_id is None:
            return "I couldn't find a task list."

        task = _find_task_by_title(service, tasklist_id, item)
        if task is None:
            return f"I couldn't find '{item}' on your list."

        try:
            service.tasks().patch(
                tasklist=tasklist_id,
                task=task["id"],
                body={"status": "completed"},
            ).execute()
        except Exception as exc:
            return f"I had trouble completing that task: {exc}"

        return f"Done — I've marked '{item}' as complete."
