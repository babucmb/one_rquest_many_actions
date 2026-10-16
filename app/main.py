from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.orchestrator import execute_workflow, get_workflow, workflow_events
from app.schemas import (
    AgentInfo,
    AgentRunResponse,
    AppointmentCreate,
    ApprovalDecision,
    ChecklistRequest,
    CustomerFollowupRequest,
    EventResponse,
    FamilyCheckinDraftRequest,
    MealPlanRequest,
    MealPlanSaveRequest,
    ReminderCreate,
    ReplyDraftRequest,
    RuntimeInfo,
    TaskCreate,
    TaskPageResponse,
    TaskResponse,
    TaskUpdate,
    TripUpdateApprovalRequest,
    WorkflowRequest,
    WorkflowResponse,
)
from app.services import (
    AGENTS,
    appointment_conflicts,
    appointments,
    budget_summary,
    business_summary,
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
    list_reminders,
    list_tasks,
    meal_plan,
    meal_preferences,
    request_trip_update_approval,
    resolve_trip_update_approval,
    run_specialist,
    save_meal_plan,
    save_reply_draft,
    shopping_list,
    task_checklist,
    travel_checklist,
    trip_summary,
    update_task_status,
)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    initialize_database()
    yield


app = FastAPI(
    title="One Request, Many Actions",
    description="Alexa+-style multi-agent workflow demo. Not an official Alexa+ integration.",
    version="1.0.0",
    lifespan=lifespan,
)
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def ready(db: Annotated[Session, Depends(get_db)]) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ready", "database": "connected"}


@app.get("/api/v1/runtime", response_model=RuntimeInfo)
def runtime_info() -> dict[str, str]:
    settings = get_settings()
    use_adk = settings.agent_mode.casefold() == "adk" or (
        settings.agent_mode.casefold() == "auto" and bool(settings.google_api_key)
    )
    return {
        "mode": "google_adk" if use_adk else "offline_demo",
        "model": settings.google_model if use_adk else "local deterministic planner",
    }


@app.get("/api/v1/agents", response_model=list[AgentInfo])
def get_agents() -> list[dict[str, str]]:
    return AGENTS


@app.get("/api/v1/agents/{agent_id}")
def get_agent(agent_id: str) -> dict[str, str]:
    agent = next((item for item in AGENTS if item["id"] == agent_id), None)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found.")
    return agent


@app.post("/api/v1/agents/{agent_id}/run", response_model=AgentRunResponse)
def run_agent(agent_id: str, body: WorkflowRequest) -> dict[str, Any]:
    if agent_id not in {item["id"] for item in AGENTS}:
        raise HTTPException(status_code=404, detail="Agent not found.")
    return {"agent": agent_id, **run_specialist(agent_id, body.request)}


@app.post("/api/v1/workflows", status_code=201, response_model=WorkflowResponse)
async def create_workflow(body: WorkflowRequest) -> dict[str, Any]:
    try:
        return await execute_workflow(body.request)
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@app.get("/api/v1/workflows/{workflow_id}", response_model=WorkflowResponse)
def read_workflow(workflow_id: str) -> dict[str, Any]:
    workflow = get_workflow(workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found.")
    return workflow


@app.get("/api/v1/workflows/{workflow_id}/events", response_model=list[EventResponse])
def read_workflow_events(workflow_id: str) -> list[dict[str, Any]]:
    events = workflow_events(workflow_id)
    if events is None:
        raise HTTPException(status_code=404, detail="Workflow not found.")
    return events


@app.get("/api/v1/tasks", response_model=TaskPageResponse)
def get_tasks(
    status: str | None = Query(default=None, pattern="^(pending|in_progress|done)$"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> dict[str, Any]:
    tasks = list_tasks(status)
    return {
        "items": tasks[offset : offset + limit],
        "total": len(tasks),
        "offset": offset,
        "limit": limit,
    }


@app.get("/api/v1/tasks/daily-plan")
def get_daily_task_plan(
    for_date: str | None = Query(default=None, max_length=10),
) -> dict[str, Any]:
    try:
        return daily_plan(for_date)
    except ValueError as error:
        raise HTTPException(
            status_code=422, detail="for_date must be an ISO date (YYYY-MM-DD)."
        ) from error


@app.get("/api/v1/tasks/{task_id}")
def read_task(task_id: str) -> dict[str, Any]:
    task = get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found.")
    return task


@app.post("/api/v1/tasks", status_code=201, response_model=TaskResponse)
def post_task(body: TaskCreate) -> dict[str, Any]:
    return create_task(body.title.strip(), body.due_date, body.priority)


@app.patch("/api/v1/tasks/{task_id}", response_model=TaskResponse)
def patch_task(task_id: str, body: TaskUpdate) -> dict[str, Any]:
    task = update_task_status(task_id, body.status)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found.")
    return task


@app.post("/api/v1/tasks/checklist")
def post_task_checklist(body: ChecklistRequest) -> dict[str, Any]:
    return task_checklist(body.task_ids)


@app.get("/api/v1/expenses")
def get_expenses(category: str | None = Query(default=None, max_length=80)) -> list[dict[str, Any]]:
    return list_expenses(category)


@app.get("/api/v1/bills")
def get_bills() -> list[dict[str, Any]]:
    return list_bills()


@app.get("/api/v1/budget/summary")
def get_budget_summary() -> dict[str, Any]:
    return budget_summary()


@app.get("/api/v1/messages")
def get_messages(query: str = Query(default="", max_length=200)) -> list[dict[str, Any]]:
    return list_messages(query)


@app.get("/api/v1/messages/{message_id}")
def read_message(message_id: str) -> dict[str, Any]:
    message = get_message(message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found.")
    return message


@app.get("/api/v1/messages/{message_id}/action-items")
def get_message_action_items(message_id: str) -> dict[str, Any]:
    result = extract_message_actions(message_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Message not found.")
    return result


@app.post("/api/v1/messages/{message_id}/draft-reply")
def post_reply_draft(message_id: str, body: ReplyDraftRequest) -> dict[str, Any]:
    message = save_reply_draft(message_id, body.reply_text.strip())
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found.")
    return message


@app.get("/api/v1/meals/preferences")
def get_meal_preferences() -> dict[str, Any]:
    return meal_preferences()


@app.get("/api/v1/meals/ingredients")
def get_meal_ingredients() -> dict[str, Any]:
    return list_ingredients()


@app.post("/api/v1/meals/plan")
def post_meal_plan(body: MealPlanRequest) -> dict[str, Any]:
    return meal_plan(body.budget)


@app.post("/api/v1/meals/plans", status_code=201)
def save_meal_plan_endpoint(body: MealPlanSaveRequest) -> dict[str, Any]:
    return save_meal_plan(body.name, body.budget)


@app.get("/api/v1/meals/shopping-list")
def get_shopping_list(
    list_id: str | None = Query(default=None, max_length=36),
) -> list[dict[str, Any]]:
    return shopping_list(list_id)


@app.get("/api/v1/trips")
def get_trips() -> list[dict[str, Any]]:
    return trip_summary()


@app.get("/api/v1/trips/{trip_id}")
def read_trip(trip_id: str) -> dict[str, Any]:
    trip = get_trip(trip_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found.")
    return trip


@app.get("/api/v1/trips/{trip_id}/checklist")
def get_trip_checklist(trip_id: str) -> dict[str, Any]:
    result = travel_checklist(trip_id)
    if result["trip"] is None:
        raise HTTPException(status_code=404, detail="Trip not found.")
    return result


@app.post("/api/v1/trips/{trip_id}/change-requests", status_code=201)
def post_trip_change_request(trip_id: str, body: TripUpdateApprovalRequest) -> dict[str, Any]:
    try:
        result = request_trip_update_approval(
            trip_id,
            body.destination,
            body.starts_on,
            body.ends_on,
            body.estimated_cost,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if result is None:
        raise HTTPException(status_code=404, detail="Trip not found.")
    return result


@app.get("/api/v1/approvals")
def get_approvals() -> list[dict[str, Any]]:
    return list_approval_requests()


@app.post("/api/v1/approvals/{approval_id}/decision")
def post_approval_decision(approval_id: str, body: ApprovalDecision) -> dict[str, Any]:
    try:
        result = resolve_trip_update_approval(approval_id, body.approved)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if result is None:
        raise HTTPException(status_code=404, detail="Approval request not found.")
    return result


@app.post("/api/v1/trips/estimate")
def estimate_trip(estimated_cost: float = Query(ge=0)) -> dict[str, Any]:
    return budget_summary(estimated_cost)


@app.get("/api/v1/appointments")
def get_appointments() -> list[dict[str, Any]]:
    return appointments()


@app.get("/api/v1/appointments/conflicts")
def get_appointment_conflicts() -> dict[str, Any]:
    return {"appointments": appointments(), "conflicts": appointment_conflicts()}


@app.post("/api/v1/appointments", status_code=201)
def post_appointment(body: AppointmentCreate) -> dict[str, Any]:
    try:
        return create_appointment(body.title.strip(), body.starts_at, body.owner.strip() or "You")
    except ValueError as error:
        raise HTTPException(
            status_code=422, detail="starts_at must be an ISO-8601 date-time."
        ) from error


@app.post("/api/v1/appointments/{appointment_id}/checkin-drafts", status_code=201)
def post_family_checkin_draft(
    appointment_id: str, body: FamilyCheckinDraftRequest
) -> dict[str, Any]:
    result = create_family_checkin_draft(appointment_id, body.message.strip())
    if result is None:
        raise HTTPException(status_code=404, detail="Appointment not found.")
    return result


@app.get("/api/v1/appointments/checkin-drafts")
def get_family_checkin_drafts() -> list[dict[str, Any]]:
    return list_family_checkin_drafts()


@app.get("/api/v1/reminders")
def get_reminders() -> list[dict[str, Any]]:
    return list_reminders()


@app.post("/api/v1/reminders", status_code=201)
def post_reminder(body: ReminderCreate) -> dict[str, Any]:
    try:
        return create_reminder(body.title.strip(), body.remind_at, body.owner.strip() or "You")
    except ValueError as error:
        raise HTTPException(
            status_code=422, detail="remind_at must be an ISO-8601 date-time."
        ) from error


@app.get("/api/v1/inventory")
def get_inventory() -> list[dict[str, Any]]:
    return list_inventory()


@app.get("/api/v1/orders")
def get_orders() -> list[dict[str, Any]]:
    return list_orders()


@app.get("/api/v1/business/summary")
def get_business() -> dict[str, Any]:
    return business_summary()


@app.post("/api/v1/orders/{order_id}/followup-drafts", status_code=201)
def post_customer_followup_draft(order_id: str, body: CustomerFollowupRequest) -> dict[str, Any]:
    result = create_customer_followup_draft(order_id, body.message.strip())
    if result is None:
        raise HTTPException(status_code=404, detail="Order not found.")
    return result


@app.get("/api/v1/orders/followup-drafts")
def get_customer_followup_drafts() -> list[dict[str, Any]]:
    return list_customer_followup_drafts()
