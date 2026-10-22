# One Request, Many Actions

**One conversation. Multiple specialist agents. Coordinated actions. You stay in control.**

An Alexa+-style workflow assistant for the Alexa+ track of the [Build, Ship, Shape: Amazon Developer Hackathon](https://amazonappdev2026.devpost.com/). The project combines a local conversational web app, a genuine MCP server using Streamable HTTP, an Agent Skill, persistent sample data, and an optional Google ADK/Gemini coordinator.

> This is an independent hackathon demo, not an official Alexa+ integration. The default app works without paid API keys. Sample mailbox, trip, budget, family, and business data are clearly labeled; no external accounts or services are connected.

## Why this fits Alexa+

The track asks for a **working MCP integration** using **Agent Skills** and **Streamable HTTP**, and permits a simulated Alexa+ experience through a web app. This project implements all three:

- `skills/one-request-many-actions/SKILL.md` gives compatible agents a portable workflow skill.
- `http://127.0.0.1:8001/mcp` is a real MCP Streamable HTTP server built with the official Python MCP SDK. It supports initialization, tool discovery, and tool execution.
- The responsive browser app provides a conversational Alexa+-style demonstration without claiming access to Alexa+ itself.
- Google ADK specialist agents and Gemini are available when a developer provides a Google API key; the no-key experience remains functional and visibly identifies itself as offline demo mode.

## What works

- Eight specialist capabilities: planning, sample inbox, meal and shopping estimates, budget, sample travel, small-business operations, sample family appointments, and accessible checklists.
- A real MCP server with 41 typed tools across all eight domains, two resources, and the `coordinate_workflow` prompt, served over Streamable HTTP or optional stdio.
- A coordinator selects relevant capabilities in offline mode, records a workflow and execution trace, and respects dependencies. For example, a trip estimate is retrieved before the budget calculation and task-planning stage.
- Independent specialists in the same stage run concurrently; dependent stages run in order. Partial specialist errors are represented instead of silently presented as successful.
- FastAPI REST endpoints and interactive OpenAPI docs at `/docs`.
- SQLAlchemy 2.x and SQLite persistence, seeded on first run.
- ADK `LlmAgent` coordinator with eight specialist subagents and an ADK `McpToolset` over Streamable HTTP.
- Real MCP client integration test that initializes a client, lists server tools, and invokes a tool.
- Persistent local meal plans and shopping lists, reminders, appointments, message/family/business drafts, and trip-change approvals. Trip edits are applied to demo data only after explicit approval; nothing is sent, purchased, paid, booked, or delivered.
- A responsive interface with execution traces, suggested requests, local-system status, and clear demo-mode disclosure.
- A project-story panel that explains the cross-app coordination problem, hackathon technology, and local demo boundaries; the “See the idea in action” button runs the multi-agent showcase request.

## Run on Windows

Use Python 3.11 or newer. From the project folder, open PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

No secret or paid service is needed for the default demo. Start the API and web app:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In a second PowerShell window, from the same project folder and activated environment, start the MCP server:

```powershell
python -m app.mcp_server
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). The API is documented at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs), and the MCP endpoint is `http://127.0.0.1:8001/mcp`.

The MCP URL is a protocol endpoint, not a webpage. A browser may show `404` at `/` or `406 Not Acceptable: Client must accept text/event-stream` at `/mcp`; that is expected for ordinary browser requests. Verify MCP using an MCP-compatible client or the included `python -m app.mcp_client --call-budget` command.

Example prompts:

- “Prepare my trip, check the budget, and organize my tasks.”
- “Plan affordable dinners and make a shopping list within my budget.”
- “Review my inbox and turn anything important into tasks.”
- “Check my family appointments and simplify my tasks into clear steps.”

For the presentation flow, open the app and select **See the idea in action**. It runs the trip, budget, and planning workflow, then displays the participating specialists and trace. The interface also explains the project idea and its Agent Skill/MCP/Streamable HTTP components without suggesting real service integrations.

The default `AGENT_MODE=auto` selects Google ADK when `GOOGLE_API_KEY` is configured; otherwise it selects the explicitly labeled offline demo planner. To require demo mode, set `AGENT_MODE=demo`. To require Gemini mode, set `AGENT_MODE=adk` and configure `GOOGLE_API_KEY` in `.env`; the MCP server must also be running. `GOOGLE_MODEL` selects the ADK model. Do not commit `.env`.

The included MCP inspection client can verify the live server from another terminal:

```powershell
python -m app.mcp_client
python -m app.mcp_client --call-budget
```

For MCP clients that launch a subprocess, set `MCP_TRANSPORT=stdio`; `.vscode/mcp.json` includes both stdio and Streamable HTTP configurations.

## Verify

With dependencies installed:

```powershell
python -m pytest
python -m ruff check app tests
```

The MCP integration test launches the real Streamable HTTP server on a free local port and exercises discovery and tool invocation. The test suite also covers multi-domain ordering, API behavior, local task/draft writes, and missing-record responses.

## API overview

| Endpoint | Purpose |
| --- | --- |
| `GET /health`, `GET /ready` | Liveness and SQLite readiness |
| `GET /api/v1/agents` | Specialist catalog |
| `POST /api/v1/workflows` | Coordinate one natural-language request |
| `GET /api/v1/workflows/{id}` | Retrieve result, agents, and trace |
| `GET /api/v1/workflows/{id}/events` | Retrieve trace events |
| `POST /api/v1/agents/{agent_id}/run` | Invoke a specialist capability |
| `/api/v1/tasks`, `/api/v1/tasks/daily-plan`, `/api/v1/tasks/checklist` | Local tasks, prioritization, and checklists |
| `/api/v1/expenses`, `/api/v1/bills`, `/api/v1/budget/summary` | Sample finance records and budget summary |
| `/api/v1/messages` and `/api/v1/messages/{id}/draft-reply` | Demo inbox search and local unsent reply drafts |
| `/api/v1/meals/plan`, `/api/v1/meals/plans`, `/api/v1/meals/shopping-list` | Meal suggestions, persisted plans, and local shopping lists |
| `/api/v1/trips`, `/api/v1/trips/{id}/change-requests`, `/api/v1/approvals` | Demo itineraries and explicit approval for local-only trip edits |
| `/api/v1/appointments`, `/api/v1/reminders`, `/api/v1/appointments/{id}/checkin-drafts` | Sample family calendar, stored reminders, and unsent drafts |
| `/api/v1/inventory`, `/api/v1/orders`, `/api/v1/orders/{id}/followup-drafts` | Demo business records and local unsent follow-up drafts |
| `GET /openapi.json` | OpenAPI schema |
| `http://127.0.0.1:8001/mcp` | Separate MCP protocol endpoint (not a REST route) |

## MCP tools

The server exposes 41 typed tools covering planning, inbox, meals and shopping, finance, travel, family, business, and accessibility. It also provides the `one-request://agents/catalog` and `one-request://demo/data-boundaries` resources and the `coordinate_workflow` prompt. Inputs are validated; tools return structured data. The underlying records are in the same SQLite database as the web app. See [docs/MCP.md](docs/MCP.md) for the complete inventory, setup, protocol coverage, and safety boundaries.

Use an MCP-compatible client configured with `http://127.0.0.1:8001/mcp` and the skill at `skills/one-request-many-actions/SKILL.md`. The MCP service binds to loopback by default and refuses non-loopback binding. The REST app is also an unauthenticated local development service. **Do not expose either service to a public network.** A production deployment needs a reviewed authentication gateway, TLS, authorization, rate limiting, and operational controls.

## Project structure

```text
app/
  adk_runtime.py      Google ADK coordinator, eight specialist agents, MCP toolset
  config.py           Environment-based configuration
  database.py         SQLAlchemy engine and session factory
  main.py             FastAPI REST API and static web application
  mcp_server.py       Official MCP SDK Streamable HTTP tools
  models.py           Persistent SQLite entities and workflow trace
  orchestrator.py     Domain selection, dependency stages, result synthesis
  services.py         Seed data and deterministic domain tools
  static/             Self-contained responsive web interface
skills/
  one-request-many-actions/SKILL.md
tests/
  test_api.py
  test_mcp.py
```

## Current boundaries and next integrations

- The offline planner intentionally uses transparent local rules rather than pretending to perform model reasoning. The LLM-backed path uses Google ADK/Gemini when configured.
- Records are local sample data. Email, calendar, travel, banking, shopping, and notifications providers are not implemented.
- The MCP service is local-development only. Public deployment and cross-origin/remote clients require an authenticated, TLS-protected deployment gateway.
- There are no external provider integrations. A trip-change request stays pending until explicitly approved, and approval updates only the local demo itinerary; reminders, shopping-list items, and drafts are stored locally and are not delivered, purchased, or sent.
- The challenge requires a working MCP integration, not an official Alexa+ account integration. The app is therefore a simulated conversational experience, as the track permits.

## Demo walkthrough

1. Launch both local processes and open the web app.
2. Submit “Prepare my trip, check the budget, and organize my tasks.”
3. Show the trace: travel data first, budget calculation second, planning last.
4. Point out the sample-data labels and the explicit statement that no booking or payment took place.
5. Show `/docs`, then connect an MCP client to `/mcp`; list the tools and invoke the budget summary.
6. Open the Agent Skill and explain that it carries the coordination and safety instructions to compatible agent clients.
7. If a Google API key is available, set `AGENT_MODE=adk` and demonstrate the ADK coordinator; otherwise show the honest offline mode.
