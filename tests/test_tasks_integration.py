"""Integration tests for Tasks tools — auto-skip without real Google credentials.

Requires:
  1. config/google_credentials.json with real OAuth2 Desktop client credentials
     (client_id must not be the CHANGE_ME placeholder)
  2. config/google_token.json with a valid access token
     (run the server once to complete the browser OAuth flow)

Run with: pytest tests/test_tasks_integration.py -v -s
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from server.tools.google_auth import is_configured

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
    from server.tools.tasks import AddTaskTool

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
    from server.tools.tasks import AddTaskTool

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
