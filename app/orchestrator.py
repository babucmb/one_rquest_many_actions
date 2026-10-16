import asyncio
import re
from typing import Any

from sqlalchemy import select

from app.config import get_settings
from app.database import SessionLocal
from app.models import Workflow, WorkflowEvent
from app.services import AGENTS, run_specialist

DOMAIN_PATTERNS: dict[str, tuple[str, ...]] = {
    "planning": (r"\b(task|tasks|plan|planning|organize|prepare|priority|checklist|to-do)\b",),
    "inbox": (r"\b(inbox|email|emails|message|messages|reply|follow-up)\b",),
    "meals": (r"\b(meal|meals|dinner|recipe|food|grocery|groceries|shopping list)\b",),
    "finance": (r"\b(budget|expense|expenses|bill|bills|spend|afford|finance|cost)\b",),
    "travel": (r"\b(trip|travel|itinerary|flight|vacation|journey)\b",),
    "business": (r"\b(business|inventory|stock|order|orders|customer)\b",),
    "family": (r"\b(family|appointment|appointments|calendar|reminder|school pickup)\b",),
    "accessibility": (r"\b(simplify|simple steps|step.by.step|easier|plain language)\b",),
}

AGENT_BY_ID = {agent["id"]: agent for agent in AGENTS}


def detect_domains(request: str) -> list[str]:
    text = request.casefold()
    domains = [
        agent_id
        for agent_id, patterns in DOMAIN_PATTERNS.items()
        if any(re.search(pattern, text) for pattern in patterns)
    ]
    return domains or ["planning"]


def _execution_stages(domains: list[str]) -> list[list[str]]:
    remaining = set(domains)
    stages: list[list[str]] = []
    if "travel" in remaining:
        stages.append(["travel"])
        remaining.remove("travel")
    if "finance" in remaining and ("travel" in domains or "meals" in domains):
        stages.append(["finance"])
        remaining.remove("finance")
    if "planning" in remaining and len(remaining) > 1:
        independent = sorted(remaining - {"planning"})
        if independent:
            stages.append(independent)
            remaining.difference_update(independent)
    if remaining:
        stages.append(sorted(remaining))
    return stages


def _event(db, workflow_id: str, agent: str, event_type: str, message: str, details=None) -> None:
    db.add(
        WorkflowEvent(
            workflow_id=workflow_id,
            agent=agent,
            event_type=event_type,
            message=message,
            details=details,
        )
    )
    db.commit()


async def _run_demo_workflow(
    workflow_id: str, request: str, domains: list[str]
) -> list[dict[str, Any]]:
    stage_results: dict[str, dict[str, Any]] = {}
    for stage in _execution_stages(domains):
        with SessionLocal() as db:
            for agent_id in stage:
                _event(
                    db,
                    workflow_id,
                    agent_id,
                    "started",
                    f"{AGENT_BY_ID[agent_id]['name']} started.",
                )

        async def execute(agent_id: str) -> tuple[str, dict[str, Any]]:
            context: dict[str, Any] = {}
            if agent_id == "finance" and "travel" in stage_results:
                travel_data = stage_results["travel"]["data"]
                trips = travel_data.get("trips", [])
                context["trip_estimate"] = trips[0]["estimated_cost"] if trips else 0
            if agent_id == "meals" and "finance" in stage_results:
                context["available_budget"] = stage_results["finance"]["data"][
                    "available_after_estimate"
                ]
            result = await asyncio.to_thread(run_specialist, agent_id, request, context)
            return agent_id, result

        pairs = await asyncio.gather(
            *(execute(agent_id) for agent_id in stage), return_exceptions=True
        )
        for agent_id, result in zip(stage, pairs, strict=True):
            if isinstance(result, BaseException):
                with SessionLocal() as db:
                    _event(db, workflow_id, agent_id, "failed", f"Agent failed: {result}")
                stage_results[agent_id] = {
                    "error": str(result),
                    "summary": "This specialist could not complete its work.",
                }
                continue
            actual_agent_id, output = result
            stage_results[actual_agent_id] = output
            with SessionLocal() as db:
                _event(
                    db,
                    workflow_id,
                    agent_id,
                    "completed",
                    output["summary"],
                    {"tool_calls": output.get("tool_calls", []), "data": output.get("data", {})},
                )
    return [
        {"agent": agent_id, **stage_results.get(agent_id, {"error": "No result"})}
        for agent_id in domains
    ]


async def _run_adk_workflow(workflow_id: str, request: str) -> tuple[list[dict[str, Any]], str]:
    from app.adk_runtime import run_coordinator

    response, trace = await run_coordinator(request)
    with SessionLocal() as db:
        for event in trace:
            _event(
                db,
                workflow_id,
                event["agent"],
                "tool_call" if event["summary"] != "Agent response" else "agent_response",
                event["summary"],
                {"message": event["message"]} if event["message"] else None,
            )
        _event(
            db,
            workflow_id,
            "coordinator",
            "completed",
            "Google ADK coordinator completed the request.",
        )
    results: dict[str, dict[str, Any]] = {}
    for event in trace:
        if event["agent"] != "workflow_coordinator":
            result = results.setdefault(
                event["agent"], {"agent": event["agent"], "summary": event["summary"], "data": {}}
            )
            if event["message"]:
                result["summary"] = event["message"][:500]
    return list(results.values()), response


async def execute_workflow(request: str) -> dict[str, Any]:
    settings = get_settings()
    mode = settings.agent_mode.casefold()
    if mode not in {"auto", "demo", "adk"}:
        raise ValueError("AGENT_MODE must be one of: auto, demo, adk.")
    has_key = bool(settings.google_api_key)
    use_adk = mode == "adk" or (mode == "auto" and has_key)
    if mode == "adk" and not has_key:
        raise RuntimeError(
            "AGENT_MODE=adk requires GOOGLE_API_KEY. Set a key or use AGENT_MODE=demo."
        )

    domains = detect_domains(request) if not use_adk else []
    with SessionLocal() as db:
        workflow = Workflow(request=request, mode="google_adk" if use_adk else "offline_demo")
        db.add(workflow)
        db.commit()
        db.refresh(workflow)
        workflow_id = workflow.id
        _event(
            db,
            workflow_id,
            "coordinator",
            "planned",
            "Google ADK coordinator selected."
            if use_adk
            else "Offline demo planner selected relevant specialists.",
            {"agents": domains, "stages": _execution_stages(domains)} if domains else None,
        )

    try:
        if use_adk:
            agents, response = await _run_adk_workflow(workflow_id, request)
        else:
            agents = await _run_demo_workflow(workflow_id, request, domains)
            successful = [item["summary"] for item in agents if "error" not in item]
            failed = [item["agent"] for item in agents if "error" in item]
            summary = " ".join(successful)
            if failed:
                summary += f" Specialist(s) needing retry: {', '.join(failed)}."
            response = (
                "I coordinated the requested demo capabilities. "
                + summary
                + " All records and prices shown are sample data; no external action was taken."
            )
        with SessionLocal() as db:
            workflow = db.get(Workflow, workflow_id)
            workflow.response = response
            workflow.status = (
                "completed" if not any("error" in item for item in agents) else "partial"
            )
            db.commit()
            for item in agents:
                agent_id = item.get("agent", "coordinator")
                if "error" not in item:
                    _event(
                        db,
                        workflow_id,
                        agent_id,
                        "result",
                        item.get("summary", "Agent result"),
                        item.get("data"),
                    )
        return get_workflow(workflow_id)
    except Exception as error:
        with SessionLocal() as db:
            workflow = db.get(Workflow, workflow_id)
            workflow.status = "failed"
            db.commit()
            _event(
                db,
                workflow_id,
                "coordinator",
                "failed",
                "Workflow could not complete.",
                {"error": str(error)},
            )
        raise


def get_workflow(workflow_id: str) -> dict[str, Any] | None:
    with SessionLocal() as db:
        workflow = db.scalar(select(Workflow).where(Workflow.id == workflow_id))
        if workflow is None:
            return None
        events = list(
            db.scalars(
                select(WorkflowEvent)
                .where(WorkflowEvent.workflow_id == workflow_id)
                .order_by(WorkflowEvent.created_at, WorkflowEvent.id)
            )
        )
        agent_results = [
            {
                "agent": event.agent,
                "summary": event.message,
                "data": event.details,
            }
            for event in events
            if event.event_type == "result"
        ]
        return {
            "id": workflow.id,
            "request": workflow.request,
            "mode": workflow.mode,
            "status": workflow.status,
            "response": workflow.response,
            "created_at": workflow.created_at,
            "agents": agent_results,
            "events": [
                {
                    "id": event.id,
                    "agent": event.agent,
                    "event_type": event.event_type,
                    "message": event.message,
                    "details": event.details,
                    "created_at": event.created_at,
                }
                for event in events
            ],
        }


def workflow_events(workflow_id: str) -> list[dict[str, Any]] | None:
    workflow = get_workflow(workflow_id)
    return workflow["events"] if workflow else None
