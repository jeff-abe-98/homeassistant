"""Smoke tests for server/tools/tasks.py."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pi.tools.tasks import (
    AddTaskTool,
    CompleteTaskTool,
    ListTasksTool,
    _find_task_by_title,
    _user_tasklist_id,
)


class TestAddTaskTool:
    @pytest.mark.asyncio
    async def test_not_configured_returns_setup_message(self):
        tool = AddTaskTool()
        with patch("pi.tools.tasks.is_configured", return_value=False):
            result = await tool.run({"item": "oat milk"}, "owner")
        assert "set up" in result.lower() or "credentials" in result.lower()

    @pytest.mark.asyncio
    async def test_service_none_returns_connection_error(self):
        tool = AddTaskTool()
        with (
            patch("pi.tools.tasks.is_configured", return_value=True),
            patch("pi.tools.tasks.build_service", return_value=None),
        ):
            result = await tool.run({"item": "oat milk"}, "owner")
        assert "couldn't connect" in result.lower()

    @pytest.mark.asyncio
    async def test_empty_item_returns_error(self):
        tool = AddTaskTool()
        mock_service = MagicMock()
        with (
            patch("pi.tools.tasks.is_configured", return_value=True),
            patch("pi.tools.tasks.build_service", return_value=mock_service),
        ):
            result = await tool.run({"item": ""}, "owner")
        assert "name" in result.lower() or "item" in result.lower()

    @pytest.mark.asyncio
    async def test_no_tasklists_returns_error(self):
        tool = AddTaskTool()
        mock_service = MagicMock()
        mock_service.tasklists().list().execute.return_value = {"items": []}
        with (
            patch("pi.tools.tasks.is_configured", return_value=True),
            patch("pi.tools.tasks.build_service", return_value=mock_service),
        ):
            result = await tool.run({"item": "oat milk"}, "owner")
        assert "couldn't find" in result.lower()

    @pytest.mark.asyncio
    async def test_item_added_returns_confirmation(self):
        mock_service = MagicMock()
        mock_service.tasklists().list().execute.return_value = {
            "items": [{"id": "list1", "title": "My Tasks"}]
        }
        mock_service.tasks().insert().execute.return_value = {"id": "task1", "title": "oat milk"}
        tool = AddTaskTool()
        with (
            patch("pi.tools.tasks.is_configured", return_value=True),
            patch("pi.tools.tasks.build_service", return_value=mock_service),
        ):
            result = await tool.run({"item": "oat milk"}, "owner")
        assert "oat milk" in result
        assert "added" in result.lower() or "done" in result.lower()

    @pytest.mark.asyncio
    async def test_api_exception_returns_friendly_message(self):
        mock_service = MagicMock()
        mock_service.tasklists().list().execute.return_value = {
            "items": [{"id": "list1", "title": "My Tasks"}]
        }
        mock_service.tasks().insert().execute.side_effect = Exception("quota exceeded")
        tool = AddTaskTool()
        with (
            patch("pi.tools.tasks.is_configured", return_value=True),
            patch("pi.tools.tasks.build_service", return_value=mock_service),
        ):
            result = await tool.run({"item": "oat milk"}, "owner")
        assert "trouble" in result.lower()


class TestListTasksTool:
    @pytest.mark.asyncio
    async def test_not_configured_returns_setup_message(self):
        tool = ListTasksTool()
        with patch("pi.tools.tasks.is_configured", return_value=False):
            result = await tool.run({"query": "what's on my list"}, "owner")
        assert "set up" in result.lower() or "credentials" in result.lower()

    @pytest.mark.asyncio
    async def test_service_none_returns_connection_error(self):
        tool = ListTasksTool()
        with (
            patch("pi.tools.tasks.is_configured", return_value=True),
            patch("pi.tools.tasks.build_service", return_value=None),
        ):
            result = await tool.run({"query": "what's on my list"}, "owner")
        assert "couldn't connect" in result.lower()

    @pytest.mark.asyncio
    async def test_empty_list_returns_empty_message(self):
        mock_service = MagicMock()
        mock_service.tasklists().list().execute.return_value = {
            "items": [{"id": "list1", "title": "My Tasks"}]
        }
        mock_service.tasks().list().execute.return_value = {"items": []}
        tool = ListTasksTool()
        with (
            patch("pi.tools.tasks.is_configured", return_value=True),
            patch("pi.tools.tasks.build_service", return_value=mock_service),
        ):
            result = await tool.run({"query": "what's on my list"}, "owner")
        assert "empty" in result.lower() or "nothing" in result.lower()

    @pytest.mark.asyncio
    async def test_tasks_narrated_via_llm(self):
        mock_service = MagicMock()
        mock_service.tasklists().list().execute.return_value = {
            "items": [{"id": "list1", "title": "My Tasks"}]
        }
        mock_service.tasks().list().execute.return_value = {
            "items": [{"id": "t1", "title": "oat milk", "status": "needsAction"}]
        }
        tool = ListTasksTool()
        with (
            patch("pi.tools.tasks.is_configured", return_value=True),
            patch("pi.tools.tasks.build_service", return_value=mock_service),
            patch.object(tool, "_llm_client") as mock_client_fn,
        ):
            mock_client_fn.return_value.complete = AsyncMock(
                return_value="You need to pick up oat milk."
            )
            result = await tool.run({"query": "what's on my list"}, "owner")
        assert result == "You need to pick up oat milk."

    @pytest.mark.asyncio
    async def test_known_user_name_in_system_prompt(self):
        mock_service = MagicMock()
        mock_service.tasklists().list().execute.return_value = {
            "items": [{"id": "list1", "title": "My Tasks"}]
        }
        mock_service.tasks().list().execute.return_value = {
            "items": [{"id": "t1", "title": "bread", "status": "needsAction"}]
        }
        tool = ListTasksTool()
        captured: list[tuple[str, str]] = []

        async def _spy(system: str, user_msg: str) -> str:
            captured.append((system, user_msg))
            return "Emily, you need to pick up bread."

        with (
            patch("pi.tools.tasks.is_configured", return_value=True),
            patch("pi.tools.tasks.build_service", return_value=mock_service),
            patch.object(tool, "_llm_client") as mock_client_fn,
        ):
            mock_client_fn.return_value.complete = AsyncMock(side_effect=_spy)
            await tool.run({"query": "what's on my list"}, "emily")

        system_prompt, _ = captured[0]
        assert "emily" in system_prompt.lower()

    @pytest.mark.asyncio
    async def test_api_exception_returns_friendly_message(self):
        mock_service = MagicMock()
        mock_service.tasklists().list().execute.return_value = {
            "items": [{"id": "list1", "title": "My Tasks"}]
        }
        mock_service.tasks().list().execute.side_effect = Exception("network error")
        tool = ListTasksTool()
        with (
            patch("pi.tools.tasks.is_configured", return_value=True),
            patch("pi.tools.tasks.build_service", return_value=mock_service),
        ):
            result = await tool.run({"query": "what's on my list"}, "owner")
        assert "trouble" in result.lower()


class TestCompleteTaskTool:
    @pytest.mark.asyncio
    async def test_not_configured_returns_setup_message(self):
        tool = CompleteTaskTool()
        with patch("pi.tools.tasks.is_configured", return_value=False):
            result = await tool.run({"item": "oat milk"}, "owner")
        assert "set up" in result.lower() or "credentials" in result.lower()

    @pytest.mark.asyncio
    async def test_service_none_returns_connection_error(self):
        tool = CompleteTaskTool()
        with (
            patch("pi.tools.tasks.is_configured", return_value=True),
            patch("pi.tools.tasks.build_service", return_value=None),
        ):
            result = await tool.run({"item": "oat milk"}, "owner")
        assert "couldn't connect" in result.lower()

    @pytest.mark.asyncio
    async def test_empty_item_returns_error(self):
        tool = CompleteTaskTool()
        mock_service = MagicMock()
        with (
            patch("pi.tools.tasks.is_configured", return_value=True),
            patch("pi.tools.tasks.build_service", return_value=mock_service),
        ):
            result = await tool.run({"item": ""}, "owner")
        assert "name" in result.lower() or "item" in result.lower()

    @pytest.mark.asyncio
    async def test_task_not_found_returns_not_found_message(self):
        mock_service = MagicMock()
        mock_service.tasklists().list().execute.return_value = {
            "items": [{"id": "list1", "title": "My Tasks"}]
        }
        mock_service.tasks().list().execute.return_value = {"items": []}
        tool = CompleteTaskTool()
        with (
            patch("pi.tools.tasks.is_configured", return_value=True),
            patch("pi.tools.tasks.build_service", return_value=mock_service),
        ):
            result = await tool.run({"item": "oat milk"}, "owner")
        assert "couldn't find" in result.lower()
        assert "oat milk" in result

    @pytest.mark.asyncio
    async def test_task_completed_returns_confirmation(self):
        mock_service = MagicMock()
        mock_service.tasklists().list().execute.return_value = {
            "items": [{"id": "list1", "title": "My Tasks"}]
        }
        mock_service.tasks().list().execute.return_value = {
            "items": [{"id": "t1", "title": "oat milk", "status": "needsAction"}]
        }
        mock_service.tasks().patch().execute.return_value = {
            "id": "t1",
            "title": "oat milk",
            "status": "completed",
        }
        tool = CompleteTaskTool()
        with (
            patch("pi.tools.tasks.is_configured", return_value=True),
            patch("pi.tools.tasks.build_service", return_value=mock_service),
        ):
            result = await tool.run({"item": "oat milk"}, "owner")
        assert "oat milk" in result
        assert "marked" in result.lower() or "done" in result.lower() or "complete" in result.lower()

    @pytest.mark.asyncio
    async def test_case_insensitive_match(self):
        mock_service = MagicMock()
        mock_service.tasklists().list().execute.return_value = {
            "items": [{"id": "list1", "title": "My Tasks"}]
        }
        mock_service.tasks().list().execute.return_value = {
            "items": [{"id": "t1", "title": "Oat Milk", "status": "needsAction"}]
        }
        mock_service.tasks().patch().execute.return_value = {"id": "t1", "status": "completed"}
        tool = CompleteTaskTool()
        with (
            patch("pi.tools.tasks.is_configured", return_value=True),
            patch("pi.tools.tasks.build_service", return_value=mock_service),
        ):
            result = await tool.run({"item": "oat milk"}, "owner")
        assert "done" in result.lower() or "marked" in result.lower() or "complete" in result.lower()

    @pytest.mark.asyncio
    async def test_api_exception_returns_friendly_message(self):
        mock_service = MagicMock()
        mock_service.tasklists().list().execute.return_value = {
            "items": [{"id": "list1", "title": "My Tasks"}]
        }
        mock_service.tasks().list().execute.return_value = {
            "items": [{"id": "t1", "title": "oat milk", "status": "needsAction"}]
        }
        mock_service.tasks().patch().execute.side_effect = Exception("network error")
        tool = CompleteTaskTool()
        with (
            patch("pi.tools.tasks.is_configured", return_value=True),
            patch("pi.tools.tasks.build_service", return_value=mock_service),
        ):
            result = await tool.run({"item": "oat milk"}, "owner")
        assert "trouble" in result.lower()


class TestFindTaskByTitle:
    def test_finds_matching_task(self):
        mock_service = MagicMock()
        mock_service.tasks().list().execute.return_value = {
            "items": [{"id": "t1", "title": "oat milk", "status": "needsAction"}]
        }
        task = _find_task_by_title(mock_service, "list1", "oat milk")
        assert task is not None
        assert task["id"] == "t1"

    def test_case_insensitive_match(self):
        mock_service = MagicMock()
        mock_service.tasks().list().execute.return_value = {
            "items": [{"id": "t1", "title": "Oat Milk", "status": "needsAction"}]
        }
        task = _find_task_by_title(mock_service, "list1", "oat milk")
        assert task is not None

    def test_no_match_returns_none(self):
        mock_service = MagicMock()
        mock_service.tasks().list().execute.return_value = {
            "items": [{"id": "t1", "title": "bread", "status": "needsAction"}]
        }
        task = _find_task_by_title(mock_service, "list1", "oat milk")
        assert task is None

    def test_api_exception_returns_none(self):
        mock_service = MagicMock()
        mock_service.tasks().list().execute.side_effect = Exception("network error")
        task = _find_task_by_title(mock_service, "list1", "oat milk")
        assert task is None


class TestUserTasklistId:
    def test_finds_matching_list_for_owner(self):
        mock_service = MagicMock()
        mock_service.tasklists().list().execute.return_value = {
            "items": [
                {"id": "owner_list", "title": "Owner"},
                {"id": "emily_list", "title": "Emily"},
            ]
        }
        assert _user_tasklist_id(mock_service, "owner") == "owner_list"

    def test_finds_matching_list_for_emily(self):
        mock_service = MagicMock()
        mock_service.tasklists().list().execute.return_value = {
            "items": [
                {"id": "owner_list", "title": "Owner"},
                {"id": "emily_list", "title": "Emily"},
            ]
        }
        assert _user_tasklist_id(mock_service, "emily") == "emily_list"

    def test_case_insensitive_match(self):
        mock_service = MagicMock()
        mock_service.tasklists().list().execute.return_value = {
            "items": [{"id": "list1", "title": "OWNER"}]
        }
        assert _user_tasklist_id(mock_service, "owner") == "list1"

    def test_unknown_user_returns_first_list(self):
        mock_service = MagicMock()
        mock_service.tasklists().list().execute.return_value = {
            "items": [{"id": "first_id", "title": "My Tasks"}]
        }
        assert _user_tasklist_id(mock_service, "unknown") == "first_id"

    def test_no_matching_list_creates_new(self):
        mock_service = MagicMock()
        mock_service.tasklists().list().execute.return_value = {
            "items": [{"id": "default", "title": "My Tasks"}]
        }
        mock_service.tasklists().insert().execute.return_value = {"id": "new_owner_list"}
        assert _user_tasklist_id(mock_service, "owner") == "new_owner_list"

    def test_empty_items_returns_none(self):
        mock_service = MagicMock()
        mock_service.tasklists().list().execute.return_value = {"items": []}
        assert _user_tasklist_id(mock_service, "owner") is None

    def test_api_exception_returns_none(self):
        mock_service = MagicMock()
        mock_service.tasklists().list().execute.side_effect = Exception("error")
        assert _user_tasklist_id(mock_service, "owner") is None


class TestAddTaskToolPerUserList:
    @pytest.mark.asyncio
    async def test_owner_uses_owner_tasklist(self):
        mock_service = MagicMock()
        mock_service.tasklists().list().execute.return_value = {
            "items": [
                {"id": "owner_list", "title": "Owner"},
                {"id": "emily_list", "title": "Emily"},
            ]
        }
        mock_service.tasks().insert().execute.return_value = {"id": "t1", "title": "eggs"}
        tool = AddTaskTool()
        with (
            patch("pi.tools.tasks.is_configured", return_value=True),
            patch("pi.tools.tasks.build_service", return_value=mock_service),
        ):
            result = await tool.run({"item": "eggs"}, "owner")
        assert "eggs" in result
        insert_call = mock_service.tasks.return_value.insert.call_args
        assert insert_call[1]["tasklist"] == "owner_list"

    @pytest.mark.asyncio
    async def test_emily_uses_emily_tasklist(self):
        mock_service = MagicMock()
        mock_service.tasklists().list().execute.return_value = {
            "items": [
                {"id": "owner_list", "title": "Owner"},
                {"id": "emily_list", "title": "Emily"},
            ]
        }
        mock_service.tasks().insert().execute.return_value = {"id": "t2", "title": "bread"}
        tool = AddTaskTool()
        with (
            patch("pi.tools.tasks.is_configured", return_value=True),
            patch("pi.tools.tasks.build_service", return_value=mock_service),
        ):
            result = await tool.run({"item": "bread"}, "emily")
        assert "bread" in result
        insert_call = mock_service.tasks.return_value.insert.call_args
        assert insert_call[1]["tasklist"] == "emily_list"
