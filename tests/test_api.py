import os
import tempfile
from pathlib import Path

import pytest

os.environ["DATABASE_URL"] = (
    f"sqlite:///{Path(tempfile.gettempdir()) / f'one-request-api-{os.getpid()}.db'}"
)
os.environ["AGENT_MODE"] = "demo"
os.environ.pop("GOOGLE_API_KEY", None)

from fastapi.testclient import TestClient
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams

from app.adk_runtime import _build_coordinator
from app.config import get_settings
from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_health_and_readiness(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/ready").json()["database"] == "connected"
    assert client.get("/api/v1/runtime").json()["mode"] == "offline_demo"


def test_adk_coordinator_has_eight_specialists_and_mcp_tools() -> None:
    toolset = McpToolset(
        connection_params=StreamableHTTPConnectionParams(url=get_settings().mcp_server_url)
    )
    coordinator = _build_coordinator(toolset)
    assert coordinator.name == "workflow_coordinator"
    assert len(coordinator.sub_agents) == 8
    assert {agent.name for agent in coordinator.sub_agents} == {
        "planning_specialist",
        "inbox_specialist",
        "meals_specialist",
        "finance_specialist",
        "travel_specialist",
        "business_specialist",
        "family_specialist",
        "accessibility_specialist",
    }


def test_adk_mode_without_api_key_fails_explicitly(client: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("AGENT_MODE", "adk")
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    get_settings.cache_clear()
    try:
        response = client.post("/api/v1/workflows", json={"request": "Plan a task."})
        assert response.status_code == 503
        assert "GOOGLE_API_KEY" in response.json()["detail"]
    finally:
        get_settings.cache_clear()


def test_agent_catalog_and_unknown_agent(client: TestClient) -> None:
    response = client.get("/api/v1/agents")
    assert response.status_code == 200
    assert len(response.json()) == 8
    assert client.get("/api/v1/agents/not-a-domain").status_code == 404


def test_multi_agent_workflow_preserves_dependencies_and_trace(client: TestClient) -> None:
    response = client.post(
        "/api/v1/workflows",
        json={"request": "Prepare my trip, check the budget, and organize my tasks."},
    )
    assert response.status_code == 201
    workflow = response.json()
    assert workflow["mode"] == "offline_demo"
    assert workflow["status"] == "completed"
    assert {result["agent"] for result in workflow["agents"]} == {"travel", "finance", "planning"}
    planned = next(event for event in workflow["events"] if event["event_type"] == "planned")
    assert planned["details"]["stages"] == [["travel"], ["finance"], ["planning"]]
    assert all(
        event["event_type"] in {"planned", "started", "completed", "result"}
        for event in workflow["events"]
    )
    assert "sample data" in workflow["response"].lower()


def test_workflow_get_and_missing_workflow(client: TestClient) -> None:
    created = client.post("/api/v1/workflows", json={"request": "Plan dinner on a budget."}).json()
    assert client.get(f"/api/v1/workflows/{created['id']}").json()["id"] == created["id"]
    assert client.get("/api/v1/workflows/missing").status_code == 404
    assert client.get(f"/api/v1/workflows/{created['id']}/events").status_code == 200


def test_meals_wait_for_budget_when_both_are_requested(client: TestClient) -> None:
    response = client.post(
        "/api/v1/workflows",
        json={"request": "Plan meals and check my budget."},
    )
    workflow = response.json()
    planned = next(event for event in workflow["events"] if event["event_type"] == "planned")
    assert planned["details"]["stages"] == [["finance"], ["meals"], ["planning"]]
    meal_result = next(result for result in workflow["agents"] if result["agent"] == "meals")
    finance_result = next(result for result in workflow["agents"] if result["agent"] == "finance")
    assert (
        meal_result["data"]["budget_constraint"]
        == finance_result["data"]["available_after_estimate"]
    )


def test_task_create_update_and_validation(client: TestClient) -> None:
    created = client.post(
        "/api/v1/tasks", json={"title": "Book a dentist appointment", "priority": "high"}
    )
    assert created.status_code == 201
    task = created.json()
    updated = client.patch(f"/api/v1/tasks/{task['id']}", json={"status": "done"})
    assert updated.status_code == 200
    assert updated.json()["status"] == "done"
    assert client.patch("/api/v1/tasks/missing", json={"status": "done"}).status_code == 404
    assert (
        client.patch(f"/api/v1/tasks/{task['id']}", json={"status": "unknown"}).status_code == 422
    )
    assert client.post("/api/v1/tasks", json={"title": "   "}).status_code == 422
    assert client.post("/api/v1/workflows", json={"request": "   "}).status_code == 422


def test_domain_endpoints_and_reply_draft_are_local(client: TestClient) -> None:
    assert client.get("/api/v1/budget/summary").json()["data_source"] == "seeded_demo_records"
    assert client.get("/api/v1/trips").json()
    assert client.get("/api/v1/appointments").json()
    assert client.get("/api/v1/inventory").json()
    message = client.get("/api/v1/messages").json()[0]
    saved = client.post(
        f"/api/v1/messages/{message['id']}/draft-reply",
        json={"reply_text": "Thanks, I will follow up."},
    )
    assert saved.status_code == 200
    assert saved.json()["reply_draft"] == "Thanks, I will follow up."
    assert "sent" not in saved.json()["reply_draft"].lower()
    family = client.post(
        "/api/v1/agents/family/run",
        json={"request": "Check family appointments for conflicts."},
    )
    assert family.status_code == 200
    assert family.json()["data"]["conflicts"] == []


def test_persisted_meal_plan_approvals_reminders_and_drafts(client: TestClient) -> None:
    saved_plan = client.post(
        "/api/v1/meals/plans",
        json={"name": "Integration test meal plan", "budget": 25},
    )
    assert saved_plan.status_code == 201
    list_id = saved_plan.json()["id"]
    shopping = client.get(f"/api/v1/meals/shopping-list?list_id={list_id}")
    assert {row["ingredient"] for row in shopping.json()} == {"green onion", "olive oil"}

    trip = client.get("/api/v1/trips").json()[0]
    change = client.post(
        f"/api/v1/trips/{trip['id']}/change-requests",
        json={"destination": "Seattle"},
    )
    assert change.status_code == 201
    approval_id = change.json()["id"]
    assert client.get(f"/api/v1/trips/{trip['id']}").json()["destination"] != "Seattle"
    resolved = client.post(
        f"/api/v1/approvals/{approval_id}/decision",
        json={"approved": True},
    )
    assert resolved.status_code == 200
    assert resolved.json()["updated_trip"]["destination"] == "Seattle"
    assert (
        client.post(
            f"/api/v1/approvals/{approval_id}/decision",
            json={"approved": True},
        ).status_code
        == 409
    )

    reminder = client.post(
        "/api/v1/reminders",
        json={"title": "Demo reminder", "remind_at": "2030-02-03T10:00:00"},
    )
    assert reminder.status_code == 201
    assert reminder.json()["delivery_status"] == "stored_locally_not_delivered"
    assert client.get("/api/v1/reminders").json()
    assert client.get("/api/v1/tasks/daily-plan?for_date=not-a-date").status_code == 422


def test_homepage_and_openapi_are_served(client: TestClient) -> None:
    homepage = client.get("/").text
    assert "One request" in homepage
    assert 'id="showcase-button"' in homepage
    assert "story-card" in homepage
    assert "Agent Skill" in homepage
    assert "Streamable HTTP" in homepage
    assert client.get("/static/styles.css").status_code == 200
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/openapi.json").status_code == 200
