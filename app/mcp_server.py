import logging
from datetime import date
from math import isfinite

from mcp.server.fastmcp import FastMCP

from app.config import get_settings
from app.services import (
    appointment_conflicts,
    appointments,
    budget_summary,
    business_summary,
    categorize_expenses,
    create_appointment,
    create_customer_followup_draft,
    create_family_checkin_draft,
    create_reminder,
    create_task,
    daily_plan,
    extract_message_actions,
    get_message,
    get_task,
    get_trip,
    initialize_database,
    list_approval_requests,
    list_bills,
    list_customer_followup_drafts,
    list_expenses,
    list_family_checkin_drafts,
    list_ingredients,
    list_inventory,
    list_messages,
    list_orders,
    list_tasks,
    meal_plan,
    meal_preferences,
    request_trip_update_approval,
    resolve_trip_update_approval,
    save_meal_plan,
    save_reply_draft,
    shopping_list,
    simplify_instructions,
    task_checklist,
    travel_checklist,
    trip_summary,
    update_task_status,
)

logging.basicConfig(level=logging.INFO)
settings = get_settings()
mcp = FastMCP(
    "one-request-many-actions",
    instructions=(
        "Local workflow tools backed by clearly labeled sample data. "
        "Drafting and planning tools never send messages, spend money, book travel, "
        "or notify people."
    ),
    host=settings.mcp_host,
    port=settings.mcp_port,
    streamable_http_path="/mcp",
)


@mcp.tool()
def list_tasks_tool(status: str | None = None) -> list[dict]:
    """List local tasks, optionally filtered by pending, in_progress, or done status."""
    if status not in {None, "pending", "in_progress", "done"}:
        raise ValueError("status must be pending, in_progress, done, or omitted")
    return list_tasks(status)


@mcp.tool()
def get_task_details_tool(task_id: str) -> dict:
    """Retrieve one local task by its identifier."""
    result = get_task(task_id)
    if result is None:
        raise ValueError("task_id was not found")
    return result


@mcp.tool()
def create_task_tool(title: str, due_date: str | None = None, priority: str = "normal") -> dict:
    """Create a local task. This changes only this demo application's SQLite data."""
    if priority not in {"low", "normal", "high"}:
        raise ValueError("priority must be low, normal, or high")
    if not title.strip():
        raise ValueError("title must not be blank")
    if due_date is not None:
        try:
            due_date = date.fromisoformat(due_date).isoformat()
        except ValueError as error:
            raise ValueError("due_date must use YYYY-MM-DD format") from error
    return create_task(title.strip(), due_date, priority)


@mcp.tool()
def update_task_status_tool(task_id: str, status: str) -> dict:
    """Update a local task status; allowed values are pending, in_progress, and done."""
    if status not in {"pending", "in_progress", "done"}:
        raise ValueError("status must be pending, in_progress, or done")
    result = update_task_status(task_id, status)
    if result is None:
        raise ValueError("task_id was not found")
    return result


@mcp.tool()
def get_daily_plan_tool(for_date: str | None = None) -> dict:
    """Create a priority-and-deadline view of local tasks for an ISO date (YYYY-MM-DD)."""
    try:
        return daily_plan(for_date)
    except ValueError as error:
        raise ValueError("for_date must use YYYY-MM-DD format") from error


@mcp.tool()
def get_budget_summary_tool(additional_estimate: float = 0) -> dict:
    """Calculate a budget summary from sample expenses and bills; no bank data or payments."""
    if not isfinite(additional_estimate) or additional_estimate < 0:
        raise ValueError("additional_estimate must be finite and non-negative")
    return budget_summary(additional_estimate)


@mcp.tool()
def list_expenses_tool(category: str | None = None) -> list[dict]:
    """List sample expenses, optionally filtered by their current category."""
    return list_expenses(category)


@mcp.tool()
def list_bills_tool() -> list[dict]:
    """List seeded example bills and due dates; this tool cannot pay a bill."""
    return list_bills()


@mcp.tool()
def categorize_expenses_tool() -> dict:
    """Apply transparent local keyword categories to seeded expense descriptions."""
    return categorize_expenses()


@mcp.tool()
def search_demo_messages_tool(query: str = "") -> list[dict]:
    """Search the included sample inbox; it does not connect to a real mailbox."""
    return list_messages(query[:200])


@mcp.tool()
def get_message_details_tool(message_id: str) -> dict:
    """Retrieve one message from the included sample inbox."""
    result = get_message(message_id)
    if result is None:
        raise ValueError("message_id was not found")
    return result


@mcp.tool()
def extract_message_action_items_tool(message_id: str) -> dict:
    """Find a possible request in one sample message; dates still require human verification."""
    result = extract_message_actions(message_id)
    if result is None:
        raise ValueError("message_id was not found")
    return result


@mcp.tool()
def create_reply_draft_tool(message_id: str, reply_text: str) -> dict:
    """Save a local reply draft for a sample message; it does not send an email."""
    if not reply_text.strip():
        raise ValueError("reply_text must not be blank")
    result = save_reply_draft(message_id, reply_text.strip())
    if result is None:
        raise ValueError("message_id was not found")
    return result


@mcp.tool()
def get_ingredients_tool() -> dict:
    """List sample pantry ingredients; quantities are not real inventory measurements."""
    return list_ingredients()


@mcp.tool()
def get_meal_preferences_tool() -> dict:
    """Retrieve locally stored meal preferences; no health or dietary inference is made."""
    return meal_preferences()


@mcp.tool()
def get_meal_plan_tool(budget: float | None = None) -> dict:
    """Suggest meals using a sample pantry and price estimates, not live product data."""
    if budget is not None and (not isfinite(budget) or budget < 0):
        raise ValueError("budget must be finite and non-negative")
    return meal_plan(budget)


@mcp.tool()
def save_meal_plan_tool(name: str, budget: float | None = None) -> dict:
    """Save a proposed meal plan and its local shopping list; nothing is purchased."""
    if not name.strip():
        raise ValueError("name must not be blank")
    if budget is not None and (not isfinite(budget) or budget < 0):
        raise ValueError("budget must be finite and non-negative")
    return save_meal_plan(name.strip(), budget)


@mcp.tool()
def get_shopping_list_tool(list_id: str | None = None) -> list[dict]:
    """Retrieve saved local shopping-list items; item costs are unknown unless stated."""
    return shopping_list(list_id)


@mcp.tool()
def get_trip_summary_tool() -> list[dict]:
    """Return the seeded trip estimate; no travel provider or booking is connected."""
    return trip_summary()


@mcp.tool()
def estimate_trip_cost_tool(trip_id: str | None = None) -> dict:
    """Check a sample trip estimate against the sample budget; it does not book travel."""
    trip = get_trip(trip_id)
    if trip is None:
        raise ValueError("trip was not found")
    return {
        "trip": trip,
        "budget_check": budget_summary(trip["estimated_cost"]),
        "data_source": "sample_itinerary_and_seeded_demo_records",
    }


@mcp.tool()
def get_travel_checklist_tool(trip_id: str | None = None) -> dict:
    """Return a preparation checklist suggestion for a sample trip."""
    result = travel_checklist(trip_id)
    if result["trip"] is None:
        raise ValueError("trip was not found")
    return result


@mcp.tool()
def request_trip_update_approval_tool(
    trip_id: str,
    destination: str | None = None,
    starts_on: str | None = None,
    ends_on: str | None = None,
    estimated_cost: float | None = None,
) -> dict:
    """Propose local itinerary edits for approval; this tool does not change the trip."""
    result = request_trip_update_approval(trip_id, destination, starts_on, ends_on, estimated_cost)
    if result is None:
        raise ValueError("trip_id was not found")
    return result


@mcp.tool()
def resolve_trip_update_approval_tool(approval_id: str, approved: bool) -> dict:
    """Apply or reject a pending local trip edit after the user explicitly decides."""
    result = resolve_trip_update_approval(approval_id, approved)
    if result is None:
        raise ValueError("approval_id was not found")
    return result


@mcp.tool()
def list_pending_approvals_tool() -> list[dict]:
    """List local trip-edit approval requests; unresolved requests have approved=null."""
    return list_approval_requests()


@mcp.tool()
def get_appointments_tool() -> list[dict]:
    """Return local sample appointments; this tool does not read or modify a real calendar."""
    return appointments()


@mcp.tool()
def check_appointment_conflicts_tool() -> dict:
    """Review sample appointments for overlaps, assuming each is a one-hour block."""

    return {
        "appointments": appointments(),
        "conflicts": appointment_conflicts(),
        "data_source": "local_demo_appointments",
    }


@mcp.tool()
def create_appointment_tool(title: str, starts_at: str, owner: str = "You") -> dict:
    """Create a local sample appointment; this does not write to a real calendar."""
    if not title.strip():
        raise ValueError("title must not be blank")
    try:
        return create_appointment(title.strip(), starts_at, owner.strip() or "You")
    except ValueError as error:
        raise ValueError("starts_at must be an ISO-8601 date-time") from error


@mcp.tool()
def create_reminder_tool(title: str, remind_at: str, owner: str = "You") -> dict:
    """Store a local reminder record; no notification is sent or delivered."""
    if not title.strip():
        raise ValueError("title must not be blank")
    try:
        return create_reminder(title.strip(), remind_at, owner.strip() or "You")
    except ValueError as error:
        raise ValueError("remind_at must be an ISO-8601 date-time") from error


@mcp.tool()
def list_reminders_tool() -> list[dict]:
    """List locally stored reminders and their not-delivered status."""
    from app.services import list_reminders

    return list_reminders()


@mcp.tool()
def create_appointment_preparation_task_tool(appointment_title: str, task_title: str) -> dict:
    """Create a local preparation task associated with a sample appointment."""
    if not appointment_title.strip() or not task_title.strip():
        raise ValueError("appointment_title and task_title must not be blank")
    return create_task(
        f"{task_title.strip()} (for {appointment_title.strip()})",
        priority="normal",
    )


@mcp.tool()
def create_family_checkin_draft_tool(appointment_id: str, message: str) -> dict:
    """Save a local family check-in draft for a sample appointment; it is not delivered."""
    if not message.strip():
        raise ValueError("message must not be blank")
    result = create_family_checkin_draft(appointment_id, message.strip())
    if result is None:
        raise ValueError("appointment_id was not found")
    return result


@mcp.tool()
def list_family_checkin_drafts_tool() -> list[dict]:
    """List locally stored check-in drafts that have not been sent."""
    return list_family_checkin_drafts()


@mcp.tool()
def get_business_summary_tool() -> dict:
    """Summarize seeded demo inventory and orders; it does not send customer messages."""
    return business_summary()


@mcp.tool()
def list_inventory_tool() -> list[dict]:
    """List sample inventory, quantities, and reorder thresholds."""
    return list_inventory()


@mcp.tool()
def list_orders_tool() -> list[dict]:
    """List sample business orders; no fulfillment or customer contact is performed."""
    return list_orders()


@mcp.tool()
def create_customer_followup_draft_tool(order_id: str, message: str) -> dict:
    """Save a local customer follow-up draft for an order; it is not sent."""
    if not message.strip():
        raise ValueError("message must not be blank")
    result = create_customer_followup_draft(order_id, message.strip())
    if result is None:
        raise ValueError("order_id was not found")
    return result


@mcp.tool()
def list_customer_followup_drafts_tool() -> list[dict]:
    """List local business follow-up drafts that have not been sent."""
    return list_customer_followup_drafts()


@mcp.tool()
def simplify_instructions_tool(text: str) -> list[str]:
    """Break user-provided text into a short numbered checklist without inferring health needs."""
    if len(text) > 4000:
        raise ValueError("text must be at most 4000 characters")
    return simplify_instructions(text)


@mcp.tool()
def create_task_checklist_tool(task_ids: list[str]) -> dict:
    """Return a short numbered checklist for task IDs and report IDs that were not found."""
    if len(task_ids) > 50:
        raise ValueError("task_ids may contain at most 50 entries")
    return task_checklist(task_ids)


@mcp.tool()
def reformat_plan_tool(steps: list[str], style: str = "numbered") -> str:
    """Reformat supplied steps as numbered, bullets, or a concise single-line plan."""
    if len(steps) > 50 or any(len(step) > 500 for step in steps):
        raise ValueError("steps may contain at most 50 entries of at most 500 characters")
    if style not in {"numbered", "bullets", "concise"}:
        raise ValueError("style must be numbered, bullets, or concise")
    clean_steps = [step.strip() for step in steps if step.strip()]
    if style == "numbered":
        return "\n".join(f"{index}. {step}" for index, step in enumerate(clean_steps, start=1))
    if style == "bullets":
        return "\n".join(f"- {step}" for step in clean_steps)
    return "Next: " + "; then ".join(clean_steps) if clean_steps else "No steps were provided."


@mcp.tool()
def summarize_workflow_results_tool(workflow_id: str) -> dict:
    """Summarize the recorded result of a local workflow by its ID."""
    from app.orchestrator import get_workflow

    workflow = get_workflow(workflow_id)
    if workflow is None:
        raise ValueError("workflow_id was not found")
    return {
        "workflow_id": workflow_id,
        "status": workflow["status"],
        "response": workflow["response"],
        "agents": workflow["agents"],
        "sample_data_disclaimer": (
            "Workflow results use local demo data unless clearly stated otherwise."
        ),
    }


@mcp.resource("one-request://agents/catalog", mime_type="application/json")
def agent_catalog_resource() -> str:
    """A catalog of the eight local workflow capabilities and their data boundaries."""
    import json

    from app.services import AGENTS

    return json.dumps({"agents": AGENTS, "data_mode": "seeded local demo data"}, ensure_ascii=False)


@mcp.resource("one-request://demo/data-boundaries")
def data_boundaries_resource() -> str:
    """Data-source and external-action limitations for this local hackathon demo."""
    return (
        "This MCP server uses local seeded demo records. No real email, bank, calendar, "
        "travel, shopping, or notification provider is connected. Local drafts, task edits, "
        "appointment records, and reminders are stored in SQLite only. Nothing is sent, "
        "paid, purchased, booked, or delivered."
    )


@mcp.prompt()
def coordinate_workflow(request: str) -> str:
    """Guide an MCP client to coordinate relevant agents and verify results."""
    if not request.strip():
        raise ValueError("request must not be blank")
    return (
        "Coordinate the user's request across only the relevant One Request, Many Actions "
        "specialists. Use discovered MCP tools for all sample data. Respect dependencies: "
        "retrieve trip estimates before budget checks; check a budget before budget-constrained "
        "meal planning; produce preparation tasks after their source results. Run independent "
        "read-only work concurrently when safe. Disclose seeded demo records and estimates. "
        "Never claim that a message was sent, money paid, shopping ordered, travel booked, "
        "a real calendar changed, or a reminder delivered. Report tool failures honestly.\n\n"
        f"User request: {request.strip()}"
    )


def main() -> None:
    transport = settings.mcp_transport.casefold()
    if transport not in {"stdio", "streamable-http"}:
        raise RuntimeError("MCP_TRANSPORT must be 'stdio' or 'streamable-http'.")
    if transport == "streamable-http" and settings.mcp_host not in {
        "127.0.0.1",
        "localhost",
        "::1",
    }:
        raise RuntimeError(
            "The MCP server is development-only and is restricted to loopback. "
            "Do not expose it publicly without an authenticated deployment gateway."
        )
    initialize_database()
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
