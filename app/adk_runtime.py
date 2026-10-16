import os
from uuid import uuid4

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
from google.genai import types

from app.config import get_settings
from app.services import AGENTS


def _specialists(toolset: McpToolset) -> list[LlmAgent]:
    specialist_instructions = {
        "planning": (
            "Prioritize the user's tasks and produce an actionable plan. Use task tools; "
            "never claim an external calendar was changed."
        ),
        "inbox": "Review only the seeded demo inbox with inbox tools. Draft, never send, messages.",
        "meals": "Use meal tools and disclose that pantry and prices are sample data.",
        "finance": (
            "Use budget tools for arithmetic. Explain that records are seeded examples; "
            "never infer bank balances or make payments."
        ),
        "travel": (
            "Use trip tools and mark itinerary and costs as simulated. "
            "Never claim to book or change travel."
        ),
        "business": ("Review sample inventory and orders. Never send customer communications."),
        "family": (
            "Use appointment tools; do not claim a reminder was delivered or a calendar changed."
        ),
        "accessibility": (
            "Use simple, respectful language and the checklist tool. "
            "Do not infer a disability or medical condition."
        ),
    }
    return [
        LlmAgent(
            name=f"{item['id']}_specialist",
            model=get_settings().google_model,
            description=item["description"],
            instruction=specialist_instructions[item["id"]],
            tools=[toolset],
        )
        for item in AGENTS
    ]


def _build_coordinator(toolset: McpToolset) -> LlmAgent:
    return LlmAgent(
        name="workflow_coordinator",
        model=get_settings().google_model,
        description="Plans one request across specialist workflow agents.",
        instruction=(
            "You are the coordinator for One Request, Many Actions. Identify relevant specialists "
            "and delegate; do not invoke every specialist for every request. Use their MCP tools "
            "for data-backed claims. Coordinate dependencies (travel before budget checks, budget "
            "before budget-constrained meals, and results before final task preparation). "
            "Combine verified results, disclose sample data, report failures, and "
            "never claim external actions such as sending, paying, booking, or changing a calendar."
        ),
        sub_agents=_specialists(toolset),
    )


async def run_coordinator(request: str) -> tuple[str, list[dict[str, str]]]:
    settings = get_settings()
    if settings.google_api_key:
        os.environ["GOOGLE_API_KEY"] = settings.google_api_key

    toolset = McpToolset(
        connection_params=StreamableHTTPConnectionParams(
            url=settings.mcp_server_url,
            timeout=10,
            sse_read_timeout=60,
        )
    )
    coordinator = _build_coordinator(toolset)
    service = InMemorySessionService()
    app_name = "one_request_many_actions"
    user_id = "local-demo-user"
    session_id = str(uuid4())
    await service.create_session(app_name=app_name, user_id=user_id, session_id=session_id)
    runner = Runner(agent=coordinator, app_name=app_name, session_service=service)
    parts: list[str] = []
    trace: list[dict[str, str]] = []
    async with toolset:
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=types.Content(role="user", parts=[types.Part(text=request)]),
        ):
            author = event.author or "coordinator"
            tool_names: list[str] = []
            event_text: list[str] = []
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        event_text.append(part.text)
                    if part.function_call and part.function_call.name:
                        tool_names.append(part.function_call.name)
            if author != "user":
                trace.append(
                    {
                        "agent": author,
                        "summary": ", ".join(tool_names) if tool_names else "Agent response",
                        "message": " ".join(event_text)[:1000],
                    }
                )
            if event.is_final_response() and event.content and event.content.parts:
                parts.extend(part.text for part in event.content.parts if part.text)
    if not parts:
        raise RuntimeError("The Google ADK coordinator returned no final response.")
    return "\n".join(parts), trace
