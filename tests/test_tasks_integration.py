"""Integration tests for Tasks tools — auto-skip without real Google credentials.

Requires:
  1. config/google_credentials.json with real OAuth2 Desktop client credentials
     (client_id must not be the CHANGE_ME placeholder)
  2. config/google_token.json with a valid access token
     (run the server once to complete the browser OAuth flow)

Run with: pytest tests/test_tasks_integration.py -v -s
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pi.tools.google_auth import is_configured

_REQUIRES_GOOGLE = pytest.mark.skipif(
    not is_configured(),
    reason=(
        "Google credentials not configured — populate config/google_credentials.json "
        "and run the server once to complete the OAuth flow (token saved to "
        "config/google_token.json)"
    ),
)


@_REQUIRES_GOOGLE
@pytest.mark.asyncio
async def test_add_oat_milk_owner_routed_to_owner_list() -> None:
    """Owner: 'Add oat milk to my list' → task inserted into Owner's task list.

    Verifies the complete add-task flow with real credentials:
    - is_configured() passes (credentials required for this test to run at all)
    - _user_tasklist_id resolves 'owner' to the Owner list (found or created)
    - tasks().insert() is called with the Owner list ID
    - the confirmation response mentions 'oat milk'

    The Google Tasks insert is mocked so no real tasks are created.
    """
    import server.tools.tasks as tasks_module
    from pi.tools.tasks import AddTaskTool

    owner_list_id = "owner_list_id_test"

    mock_service = MagicMock()
    mock_service.tasklists().list().execute.return_value = {
        "items": [
            {"id": owner_list_id, "title": "Owner"},
            {"id": "emily_list_id_test", "title": "Emily"},
        ]
    }
    mock_service.tasks().insert().execute.return_value = {
        "id": "new_task_id",
        "title": "oat milk",
    }

    tool = AddTaskTool()

    with patch.object(tasks_module, "build_service", return_value=mock_service):
        result = await tool.run({"item": "oat milk"}, user="owner")

    assert isinstance(result, str), "tool must return a string"
    assert "oat milk" in result, f"response should mention 'oat milk': {result!r}"
    assert "done" in result.lower() or "added" in result.lower(), (
        f"response should confirm the add: {result!r}"
    )

    # Verify the insert was called with the Owner list ID
    insert_call = mock_service.tasks.return_value.insert.call_args
    assert insert_call is not None, "tasks().insert() was never called"
    assert insert_call[1].get("tasklist") == owner_list_id, (
        f"Expected insert into Owner list '{owner_list_id}', "
        f"got tasklist={insert_call[1].get('tasklist')!r}"
    )
    assert insert_call[1].get("body", {}).get("title") == "oat milk", (
        f"Expected task title 'oat milk', got {insert_call[1].get('body')!r}"
    )


@_REQUIRES_GOOGLE
@pytest.mark.asyncio
async def test_add_oat_milk_emily_routed_to_emily_list() -> None:
    """Emily: 'Add oat milk to my list' → task inserted into Emily's task list, not Owner's.

    Verifies that per-user list routing isolates Emily's tasks from Owner's.
    """
    import server.tools.tasks as tasks_module
    from pi.tools.tasks import AddTaskTool

    emily_list_id = "emily_list_id_test"

    mock_service = MagicMock()
    mock_service.tasklists().list().execute.return_value = {
        "items": [
            {"id": "owner_list_id_test", "title": "Owner"},
            {"id": emily_list_id, "title": "Emily"},
        ]
    }
    mock_service.tasks().insert().execute.return_value = {
        "id": "new_task_id",
        "title": "oat milk",
    }

    tool = AddTaskTool()

    with patch.object(tasks_module, "build_service", return_value=mock_service):
        result = await tool.run({"item": "oat milk"}, user="emily")

    assert isinstance(result, str)
    assert "oat milk" in result, f"response should mention 'oat milk': {result!r}"
    assert "done" in result.lower() or "added" in result.lower(), (
        f"response should confirm the add: {result!r}"
    )

    # Verify insert was called with Emily's list ID (not Owner's)
    insert_call = mock_service.tasks.return_value.insert.call_args
    assert insert_call is not None, "tasks().insert() was never called"
    assert insert_call[1].get("tasklist") == emily_list_id, (
        f"Expected insert into Emily list '{emily_list_id}', "
        f"got tasklist={insert_call[1].get('tasklist')!r}"
    )
    assert insert_call[1].get("body", {}).get("title") == "oat milk"


@_REQUIRES_GOOGLE
@pytest.mark.asyncio
async def test_list_tasks_owner_reads_from_owner_list() -> None:
    """Owner: 'What's on my list?' → incomplete items read from Owner's task list.

    Verifies the complete list-tasks flow with real credentials:
    - is_configured() passes (credentials required for this test to run at all)
    - _user_tasklist_id resolves 'owner' to the Owner list
    - tasks().list() is called with the Owner list ID and showCompleted=False
    - the LLM narrates the returned items
    - the response is non-empty

    The Google Tasks list call is mocked so no live API requests are made.
    """
    import server.tools.tasks as tasks_module
    from pi.tools.tasks import ListTasksTool

    owner_list_id = "owner_list_id_test"
    mock_service = MagicMock()
    mock_service.tasklists().list().execute.return_value = {
        "items": [
            {"id": owner_list_id, "title": "Owner"},
            {"id": "emily_list_id_test", "title": "Emily"},
        ]
    }
    mock_service.tasks().list().execute.return_value = {
        "items": [
            {"id": "t1", "title": "oat milk", "status": "needsAction"},
            {"id": "t2", "title": "eggs", "status": "needsAction"},
        ]
    }

    tool = ListTasksTool()

    with (
        patch.object(tasks_module, "build_service", return_value=mock_service),
        patch.object(tool, "_llm_client") as mock_client_fn,
    ):
        mock_client_fn.return_value.complete = AsyncMock(
            return_value="You have oat milk and eggs on your list."
        )
        result = await tool.run({"query": "What's on my list?"}, user="owner")

    assert isinstance(result, str), "tool must return a string"
    assert result, "response must be non-empty"

    # Verify tasks().list() was called with the Owner list ID and showCompleted=False
    list_call = mock_service.tasks.return_value.list.call_args
    assert list_call is not None, "tasks().list() was never called"
    assert list_call[1].get("tasklist") == owner_list_id, (
        f"Expected tasks read from Owner list '{owner_list_id}', "
        f"got tasklist={list_call[1].get('tasklist')!r}"
    )
    assert list_call[1].get("showCompleted") is False, (
        "tasks().list() must pass showCompleted=False to exclude completed items"
    )


@_REQUIRES_GOOGLE
@pytest.mark.asyncio
async def test_list_tasks_emily_reads_from_emily_list() -> None:
    """Emily: 'What's on my list?' → incomplete items read from Emily's list, not Owner's.

    Verifies per-user list isolation for reads (parallel to the add-oat-milk routing tests):
    - _user_tasklist_id resolves 'emily' to Emily's list
    - tasks().list() uses Emily's list ID, not Owner's
    - showCompleted=False is passed (only incomplete items returned)
    """
    import server.tools.tasks as tasks_module
    from pi.tools.tasks import ListTasksTool

    emily_list_id = "emily_list_id_test"
    mock_service = MagicMock()
    mock_service.tasklists().list().execute.return_value = {
        "items": [
            {"id": "owner_list_id_test", "title": "Owner"},
            {"id": emily_list_id, "title": "Emily"},
        ]
    }
    mock_service.tasks().list().execute.return_value = {
        "items": [
            {"id": "t3", "title": "shampoo", "status": "needsAction"},
        ]
    }

    tool = ListTasksTool()

    with (
        patch.object(tasks_module, "build_service", return_value=mock_service),
        patch.object(tool, "_llm_client") as mock_client_fn,
    ):
        mock_client_fn.return_value.complete = AsyncMock(
            return_value="Emily, you have shampoo on your list."
        )
        result = await tool.run({"query": "What's on my list?"}, user="emily")

    assert isinstance(result, str)
    assert result

    # Verify tasks().list() used Emily's list ID, not Owner's
    list_call = mock_service.tasks.return_value.list.call_args
    assert list_call is not None, "tasks().list() was never called"
    assert list_call[1].get("tasklist") == emily_list_id, (
        f"Expected tasks read from Emily list '{emily_list_id}', "
        f"got tasklist={list_call[1].get('tasklist')!r}"
    )
    assert list_call[1].get("showCompleted") is False, (
        "tasks().list() must pass showCompleted=False to exclude completed items"
    )


@_REQUIRES_GOOGLE
@pytest.mark.asyncio
async def test_mark_oat_milk_done_owner() -> None:
    """Owner: 'Mark oat milk as done' → task patched to completed in Owner's list.

    Verifies the complete complete-task flow with real credentials:
    - _user_tasklist_id resolves 'owner' to the Owner list
    - _find_task_by_title searches the Owner list and finds 'oat milk'
    - tasks().patch() is called with the Owner list ID, the task ID, and
      body={"status": "completed"}
    - the response confirms completion

    The Google Tasks API calls are mocked so no live changes are made.
    """
    import server.tools.tasks as tasks_module
    from pi.tools.tasks import CompleteTaskTool

    owner_list_id = "owner_list_id_test"
    task_id = "t1"

    mock_service = MagicMock()
    mock_service.tasklists().list().execute.return_value = {
        "items": [
            {"id": owner_list_id, "title": "Owner"},
            {"id": "emily_list_id_test", "title": "Emily"},
        ]
    }
    mock_service.tasks().list().execute.return_value = {
        "items": [
            {"id": task_id, "title": "oat milk", "status": "needsAction"},
        ]
    }
    mock_service.tasks().patch().execute.return_value = {
        "id": task_id,
        "title": "oat milk",
        "status": "completed",
    }

    tool = CompleteTaskTool()

    with patch.object(tasks_module, "build_service", return_value=mock_service):
        result = await tool.run({"item": "oat milk"}, user="owner")

    assert isinstance(result, str), "tool must return a string"
    assert "oat milk" in result, f"response should mention 'oat milk': {result!r}"
    assert "done" in result.lower() or "complet" in result.lower(), (
        f"response should confirm completion: {result!r}"
    )

    # Verify tasks().list() searched the Owner list for the task
    list_call = mock_service.tasks.return_value.list.call_args
    assert list_call is not None, "tasks().list() was never called"
    assert list_call[1].get("tasklist") == owner_list_id, (
        f"Expected task search in Owner list '{owner_list_id}', "
        f"got tasklist={list_call[1].get('tasklist')!r}"
    )

    # Verify tasks().patch() was called with the correct args
    patch_call = mock_service.tasks.return_value.patch.call_args
    assert patch_call is not None, "tasks().patch() was never called"
    assert patch_call[1].get("tasklist") == owner_list_id, (
        f"Expected patch in Owner list '{owner_list_id}', "
        f"got tasklist={patch_call[1].get('tasklist')!r}"
    )
    assert patch_call[1].get("task") == task_id, (
        f"Expected task ID '{task_id}', got task={patch_call[1].get('task')!r}"
    )
    assert patch_call[1].get("body") == {"status": "completed"}, (
        f"Expected body={{'status': 'completed'}}, got {patch_call[1].get('body')!r}"
    )


@_REQUIRES_GOOGLE
@pytest.mark.asyncio
async def test_mark_oat_milk_done_emily() -> None:
    """Emily: 'Mark oat milk as done' → task patched in Emily's list, not Owner's.

    Verifies per-user list isolation for task completion:
    - _user_tasklist_id resolves 'emily' to Emily's list
    - tasks().patch() uses Emily's list ID, not Owner's
    - body={"status": "completed"} is passed
    """
    import server.tools.tasks as tasks_module
    from pi.tools.tasks import CompleteTaskTool

    emily_list_id = "emily_list_id_test"
    task_id = "t2"

    mock_service = MagicMock()
    mock_service.tasklists().list().execute.return_value = {
        "items": [
            {"id": "owner_list_id_test", "title": "Owner"},
            {"id": emily_list_id, "title": "Emily"},
        ]
    }
    mock_service.tasks().list().execute.return_value = {
        "items": [
            {"id": task_id, "title": "oat milk", "status": "needsAction"},
        ]
    }
    mock_service.tasks().patch().execute.return_value = {
        "id": task_id,
        "title": "oat milk",
        "status": "completed",
    }

    tool = CompleteTaskTool()

    with patch.object(tasks_module, "build_service", return_value=mock_service):
        result = await tool.run({"item": "oat milk"}, user="emily")

    assert isinstance(result, str)
    assert "oat milk" in result, f"response should mention 'oat milk': {result!r}"
    assert "done" in result.lower() or "complet" in result.lower(), (
        f"response should confirm completion: {result!r}"
    )

    # Verify tasks().list() searched Emily's list, not Owner's
    list_call = mock_service.tasks.return_value.list.call_args
    assert list_call is not None, "tasks().list() was never called"
    assert list_call[1].get("tasklist") == emily_list_id, (
        f"Expected task search in Emily list '{emily_list_id}', "
        f"got tasklist={list_call[1].get('tasklist')!r}"
    )

    # Verify tasks().patch() used Emily's list ID, not Owner's
    patch_call = mock_service.tasks.return_value.patch.call_args
    assert patch_call is not None, "tasks().patch() was never called"
    assert patch_call[1].get("tasklist") == emily_list_id, (
        f"Expected patch in Emily list '{emily_list_id}', "
        f"got tasklist={patch_call[1].get('tasklist')!r}"
    )
    assert patch_call[1].get("task") == task_id, (
        f"Expected task ID '{task_id}', got task={patch_call[1].get('task')!r}"
    )
    assert patch_call[1].get("body") == {"status": "completed"}, (
        f"Expected body={{'status': 'completed'}}, got {patch_call[1].get('body')!r}"
    )
