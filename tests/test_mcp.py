import asyncio
import json
import os
import socket
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from pydantic import TypeAdapter
from pydantic.networks import AnyUrl


def _mcp_payload(result):
    data = result.structuredContent
    if data is None and result.content and result.content[0].type == "text":
        try:
            data = json.loads(result.content[0].text)
        except json.JSONDecodeError:
            return result.content[0].text
    if isinstance(data, dict) and set(data) == {"result"}:
        return data["result"]
    return data


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.mark.asyncio
async def test_real_mcp_streamable_http_discovery_and_invocation() -> None:
    port = _free_port()
    database_path = Path(tempfile.gettempdir()) / f"one-request-mcp-{os.getpid()}.db"
    env = os.environ.copy()
    env.update(
        {
            "DATABASE_URL": f"sqlite:///{database_path}",
            "MCP_HOST": "127.0.0.1",
            "MCP_PORT": str(port),
            "PYTHONUNBUFFERED": "1",
        }
    )
    process = subprocess.Popen(
        [sys.executable, "-m", "app.mcp_server"],
        cwd=Path(__file__).parents[1],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{port}/mcp"
    try:
        for _ in range(100):
            if process.poll() is not None:
                pytest.fail("MCP server exited before becoming ready.")
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                    break
            except OSError:
                await asyncio.sleep(0.1)
        else:
            pytest.fail("MCP Streamable HTTP server did not become ready.")

        async with streamable_http_client(url) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                tools = await session.list_tools()
                names = {tool.name for tool in tools.tools}
                assert "get_budget_summary_tool" in names
                assert "list_tasks_tool" in names
                assert len(names) == 41
                expected_tools = {
                    "list_tasks_tool",
                    "get_daily_plan_tool",
                    "get_task_details_tool",
                    "create_task_tool",
                    "update_task_status_tool",
                    "get_budget_summary_tool",
                    "list_expenses_tool",
                    "list_bills_tool",
                    "categorize_expenses_tool",
                    "search_demo_messages_tool",
                    "get_message_details_tool",
                    "extract_message_action_items_tool",
                    "create_reply_draft_tool",
                    "get_ingredients_tool",
                    "get_meal_preferences_tool",
                    "get_meal_plan_tool",
                    "save_meal_plan_tool",
                    "get_shopping_list_tool",
                    "get_trip_summary_tool",
                    "estimate_trip_cost_tool",
                    "get_travel_checklist_tool",
                    "request_trip_update_approval_tool",
                    "resolve_trip_update_approval_tool",
                    "list_pending_approvals_tool",
                    "get_appointments_tool",
                    "check_appointment_conflicts_tool",
                    "create_appointment_tool",
                    "create_reminder_tool",
                    "list_reminders_tool",
                    "create_appointment_preparation_task_tool",
                    "create_family_checkin_draft_tool",
                    "list_family_checkin_drafts_tool",
                    "get_business_summary_tool",
                    "list_inventory_tool",
                    "list_orders_tool",
                    "create_customer_followup_draft_tool",
                    "list_customer_followup_drafts_tool",
                    "simplify_instructions_tool",
                    "create_task_checklist_tool",
                    "reformat_plan_tool",
                    "summarize_workflow_results_tool",
                }
                assert expected_tools == names
                result = await session.call_tool(
                    "get_budget_summary_tool", {"additional_estimate": 100}
                )
                assert not result.isError
                data = _mcp_payload(result)
                assert data["additional_estimate"] == 100
                assert data["data_source"] == "seeded_demo_records"
                prompts = await session.list_prompts()
                assert "coordinate_workflow" in {prompt.name for prompt in prompts.prompts}
                prompt = await session.get_prompt(
                    "coordinate_workflow",
                    {"request": "Plan meals within a budget."},
                )
                assert "Plan meals within a budget." in prompt.messages[0].content.text
                resources = await session.list_resources()
                resource_uris = {str(resource.uri) for resource in resources.resources}
                assert "one-request://agents/catalog" in resource_uris
                boundaries = await session.read_resource(
                    TypeAdapter(AnyUrl).validate_python("one-request://demo/data-boundaries")
                )
                assert "No real email" in boundaries.contents[0].text

                invalid = await session.call_tool(
                    "get_budget_summary_tool", {"additional_estimate": -1}
                )
                assert invalid.isError

                created_task_result = await session.call_tool(
                    "create_task_tool",
                    {"title": "MCP integration test task", "priority": "high"},
                )
                assert not created_task_result.isError
                created_task = _mcp_payload(created_task_result)
                task_id = created_task["id"]
                assert (await session.call_tool("list_tasks_tool", {})).isError is False
                task_details = await session.call_tool(
                    "get_task_details_tool", {"task_id": task_id}
                )
                assert _mcp_payload(task_details)["title"] == "MCP integration test task"
                assert not (
                    await session.call_tool(
                        "update_task_status_tool",
                        {"task_id": task_id, "status": "done"},
                    )
                ).isError
                assert not (await session.call_tool("get_daily_plan_tool", {})).isError
                checklist = await session.call_tool(
                    "create_task_checklist_tool", {"task_ids": [task_id]}
                )
                assert _mcp_payload(checklist)["steps"][0]["title"] == "MCP integration test task"
                assert not (
                    await session.call_tool(
                        "reformat_plan_tool",
                        {"steps": ["Read request", "Prepare answer"], "style": "bullets"},
                    )
                ).isError

                messages = _mcp_payload(
                    await session.call_tool("search_demo_messages_tool", {"query": ""})
                )
                message_id = messages[0]["id"]
                assert not (
                    await session.call_tool("get_message_details_tool", {"message_id": message_id})
                ).isError
                assert not (
                    await session.call_tool(
                        "extract_message_action_items_tool", {"message_id": message_id}
                    )
                ).isError
                draft_result = await session.call_tool(
                    "create_reply_draft_tool",
                    {"message_id": message_id, "reply_text": "MCP test draft, not sent."},
                )
                assert not draft_result.isError

                assert not (await session.call_tool("get_ingredients_tool", {})).isError
                assert not (await session.call_tool("get_meal_preferences_tool", {})).isError
                assert not (await session.call_tool("get_meal_plan_tool", {"budget": 25})).isError
                meal = await session.call_tool(
                    "save_meal_plan_tool",
                    {"name": "MCP persisted demo plan", "budget": 25},
                )
                assert not meal.isError
                meal_data = _mcp_payload(meal)
                assert meal_data["name"] == "MCP persisted demo plan"
                assert {item["ingredient"] for item in meal_data["shopping_list"]} == {
                    "green onion",
                    "olive oil",
                }
                assert not (await session.call_tool("get_shopping_list_tool", {})).isError

                for name, arguments in (
                    ("list_expenses_tool", {}),
                    ("list_bills_tool", {}),
                    ("categorize_expenses_tool", {}),
                ):
                    assert not (await session.call_tool(name, arguments)).isError

                trip_result = await session.call_tool("get_trip_summary_tool", {})
                trips = _mcp_payload(trip_result)
                trip_id = trips[0]["id"]
                assert not (
                    await session.call_tool("estimate_trip_cost_tool", {"trip_id": trip_id})
                ).isError
                assert not (
                    await session.call_tool("get_travel_checklist_tool", {"trip_id": trip_id})
                ).isError
                proposed = await session.call_tool(
                    "request_trip_update_approval_tool",
                    {"trip_id": trip_id, "destination": "Seattle"},
                )
                proposed_data = _mcp_payload(proposed)
                assert proposed_data["status"] == "awaiting_explicit_approval"
                assert not (await session.call_tool("list_pending_approvals_tool", {})).isError
                unchanged_trip = await session.call_tool("get_trip_summary_tool", {})
                unchanged_trips = _mcp_payload(unchanged_trip)
                assert unchanged_trips[0]["destination"] != "Seattle"
                approved = await session.call_tool(
                    "resolve_trip_update_approval_tool",
                    {"approval_id": proposed_data["id"], "approved": True},
                )
                assert not approved.isError
                assert not (await session.call_tool("get_appointments_tool", {})).isError
                assert not (await session.call_tool("check_appointment_conflicts_tool", {})).isError
                appointment_result = await session.call_tool(
                    "create_appointment_tool",
                    {"title": "MCP sample appointment", "starts_at": "2030-02-03T11:30:00"},
                )
                assert not appointment_result.isError
                appointment_id = _mcp_payload(appointment_result)["id"]
                reminder_result = await session.call_tool(
                    "create_reminder_tool",
                    {"title": "MCP local reminder", "remind_at": "2030-02-03T10:00:00"},
                )
                assert not reminder_result.isError
                assert (
                    _mcp_payload(reminder_result)["delivery_status"]
                    == "stored_locally_not_delivered"
                )
                assert not (await session.call_tool("list_reminders_tool", {})).isError
                assert not (
                    await session.call_tool(
                        "create_appointment_preparation_task_tool",
                        {"appointment_title": "MCP appointment", "task_title": "Bring documents"},
                    )
                ).isError
                assert not (
                    await session.call_tool(
                        "create_family_checkin_draft_tool",
                        {"appointment_id": appointment_id, "message": "Checking in; local draft."},
                    )
                ).isError
                assert not (await session.call_tool("list_family_checkin_drafts_tool", {})).isError

                assert not (await session.call_tool("get_business_summary_tool", {})).isError
                inventory = _mcp_payload(await session.call_tool("list_inventory_tool", {}))
                orders = _mcp_payload(await session.call_tool("list_orders_tool", {}))
                customer_draft = await session.call_tool(
                    "create_customer_followup_draft_tool",
                    {"order_id": orders[0]["id"], "message": "MCP draft only."},
                )
                assert not customer_draft.isError
                assert _mcp_payload(customer_draft)["delivery_status"] == "draft_saved_not_sent"
                assert not (
                    await session.call_tool("list_customer_followup_drafts_tool", {})
                ).isError
                assert inventory
                assert not (
                    await session.call_tool(
                        "simplify_instructions_tool",
                        {"text": "Review the trip. Pack documents."},
                    )
                ).isError

                with sqlite3.connect(database_path) as connection:
                    connection.execute(
                        "INSERT INTO workflows "
                        "(id, request, mode, status, response, created_at) "
                        "VALUES (?, ?, ?, ?, ?, ?)",
                        (
                            "mcp-summary-test-workflow",
                            "Test MCP summary",
                            "offline_demo",
                            "completed",
                            "MCP summary fixture",
                            "2030-01-01 00:00:00",
                        ),
                    )
                workflow_summary = await session.call_tool(
                    "summarize_workflow_results_tool",
                    {"workflow_id": "mcp-summary-test-workflow"},
                )
                assert _mcp_payload(workflow_summary)["response"] == "MCP summary fixture"
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
