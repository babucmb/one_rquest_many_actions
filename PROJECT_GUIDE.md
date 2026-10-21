# One Request, Many Actions — Project Guide

This guide explains the project from its purpose and architecture through local setup, workflows, MCP integration, APIs, testing, troubleshooting, and the remaining production work.

## 1. Project at a glance

**One Request, Many Actions** is an Alexa+-style assistant demo. A user enters one natural-language goal; a coordinator selects relevant specialist capabilities, runs them in an order that respects simple dependencies, and presents a combined response with an inspectable execution trace.

The project is intended for the Alexa+ track of the Build, Ship, Shape: Amazon Developer Hackathon. It demonstrates a simulated assistant web app, an Agent Skill, and a working Model Context Protocol (MCP) server using Streamable HTTP. It is **not an official Alexa+ integration**.

### What the complete local demo contains

- A browser-based conversational experience.
- A FastAPI REST API and OpenAPI documentation.
- Eight specialist domains: planning, inbox, meals, finance, travel, family, business, and accessibility.
- An offline deterministic coordinator that runs without API keys.
- An optional Google ADK/Gemini coordinator for developers who configure a Google API key.
- A separate MCP server with **41 tools, two resources, and one prompt**, using Streamable HTTP or optional stdio.
- SQLite persistence shared by the web/API and MCP processes.
- A portable Agent Skill at `skills/one-request-many-actions/SKILL.md`.
- Automated API, MCP, and concurrent database-startup tests.

### Honest data and action boundaries

The included mailbox, budget, trip, appointments, inventory, and orders are sample/demo data. There are no real integrations with email, banking, calendars, travel, shopping, or notifications.

- Drafts are stored locally and are not sent.
- Reminders are stored locally and are not delivered.
- Shopping lists are saved locally; no order is placed.
- A trip change remains pending until explicitly approved. Approval updates only the local demo itinerary, not a real booking.
- Task, appointment, preference, and other records belong to the local SQLite database.
- Prices, pantry contents, and estimates are illustrative, not live data.

## 2. How the system works

```text
Browser
  └── FastAPI web/API process (127.0.0.1:8000)
        ├── Static HTML/CSS/JavaScript UI
        ├── REST API and workflow coordinator
        └── SQLite database

MCP-compatible client
  └── MCP process (127.0.0.1:8001/mcp)
        └── Same SQLite database and shared domain services

Optional ADK/Gemini workflow:
FastAPI coordinator → Google ADK specialist agents → MCP Streamable HTTP tools
```

The two server processes are separate, but use the same database URL. Start them from the project directory with the same environment/configuration so they open the same SQLite file.

### Offline workflow lifecycle

1. The browser posts a request to `POST /api/v1/workflows`.
2. The local coordinator detects relevant domains using transparent keyword patterns in `app/orchestrator.py`. If no domain matches, it selects planning.
3. It creates a workflow record and event trace in SQLite.
4. It orders dependent work into stages. For example, travel data is fetched before a budget check; when meals and finance are requested together, finance runs before budget-constrained meal planning.
5. Independent specialists in a stage can run concurrently. Specialist outputs and failures are recorded; failed work is not reported as a success.
6. The UI shows the response, participating specialists, results, and execution events.

The offline mode is deterministic workflow logic, not a generative language model. It is designed to remain usable and demonstrable without keys or network-connected providers.

### Optional ADK/Gemini workflow

With `AGENT_MODE=auto` and a configured `GOOGLE_API_KEY`, the app selects Google ADK. With `AGENT_MODE=adk`, the key is required; missing it returns an explicit service error. The ADK coordinator has eight specialist subagents and connects to the MCP server through Streamable HTTP. Therefore, both the web app and MCP server need to be running for this mode.

Live Gemini execution depends on the user's credentials and network and has not been verified as part of the no-key demo. Use `AGENT_MODE=demo` for a predictable offline presentation.

## 3. Requirements and first-time installation

### Requirements

- Windows with PowerShell (the commands in this guide use Windows paths and PowerShell syntax).
- Python 3.11 or newer.
- Internet access for the initial Python package installation.
- No API key is required for the default demo.

### Install into a virtual environment

Open PowerShell and run:

```powershell
Set-Location D:\CMB_Desktop\one_request_many_actions
python --version
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

If PowerShell blocks activation, either allow the script for the current user according to your device policy, or skip activation and use the virtual environment's interpreter directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

The `dev` extra installs the test, lint, and HTTP client dependencies in addition to the app dependencies. The checked-in `pyproject.toml` pins the project's core and development package versions.

### Configuration file (optional)

The project has defaults that run without a `.env` file. To create one from the example:

```powershell
Copy-Item .env.example .env
```

Edit `.env` only if you need to change configuration. Never commit API keys or other secrets.

| Setting | Default | Purpose |
| --- | --- | --- |
| `AGENT_MODE` | `auto` | `demo`, `auto`, or `adk`. `auto` uses ADK only when a Google key is set. |
| `GOOGLE_API_KEY` | empty | Optional credential for Google ADK/Gemini mode. |
| `GOOGLE_MODEL` | `gemini-2.5-flash` | Model name used in ADK mode. |
| `DATABASE_URL` | `sqlite:///./data/one_request_many_actions.db` | Shared database used by both processes; relative paths are relative to the working directory. |
| `MCP_SERVER_URL` | `http://127.0.0.1:8001/mcp` | MCP URL used by the ADK runtime and inspection client. |
| `MCP_TRANSPORT` | `streamable-http` | MCP server transport: `streamable-http` or `stdio`. |
| `MCP_HOST` | `127.0.0.1` | MCP HTTP bind host. HTTP mode rejects non-loopback hosts. |
| `MCP_PORT` | `8001` | MCP HTTP port. |

Settings are read from environment variables and `.env` through `pydantic-settings`. Environment variables take precedence.

## 4. Run the full project locally

Run the web app and the MCP server in **two separate PowerShell terminals**. Keep both open while using the app.

### Terminal 1: web app and REST API

```powershell
Set-Location D:\CMB_Desktop\one_request_many_actions
.\.venv\Scripts\Activate.ps1
$env:AGENT_MODE = "demo"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Terminal 2: MCP server

```powershell
Set-Location D:\CMB_Desktop\one_request_many_actions
.\.venv\Scripts\Activate.ps1
$env:MCP_TRANSPORT = "streamable-http"
python -m app.mcp_server
```

The project initializes the SQLite schema and seeds example data on first startup. Both processes can safely initialize concurrently. Database state persists between restarts by default.

### Open the local surfaces

| Purpose | Address |
| --- | --- |
| Browser app | [http://127.0.0.1:8000](http://127.0.0.1:8000) |
| Interactive API docs | [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) |
| API readiness check | [http://127.0.0.1:8000/ready](http://127.0.0.1:8000/ready) |
| MCP endpoint for clients | `http://127.0.0.1:8001/mcp` |

**Do not browse to the MCP server's `/` path.** It is not a website and can return `404`. The MCP route is `/mcp`; MCP clients communicate with it using the MCP protocol. A browser visit to `/mcp` may also not render a useful page.

### Try an end-to-end request

In the web app, submit:

> Prepare my trip, check the budget, and organize my tasks.

In demo mode, the app should coordinate travel, finance, and planning, then display their results and execution trace. All displayed trip and budget information is sample data.

Other example requests:

- “Plan affordable dinners and make a shopping list within my budget.”
- “Review my inbox and turn anything important into tasks.”
- “Check my family appointments and simplify my tasks into clear steps.”
- “Review my business inventory and prepare customer follow-ups.”

### Verify the MCP server using the included client

Open a third terminal in the project directory, activate `.venv`, then run:

```powershell
python -m app.mcp_client
```

This initializes an MCP session and prints the server identity, tools, resources, and prompts. To also invoke the budget tool:

```powershell
python -m app.mcp_client --call-budget
```

Successful output lists 41 tools, `one-request://agents/catalog`, `one-request://demo/data-boundaries`, and the `coordinate_workflow` prompt, followed by the budget-tool result.

### Stop the servers

Press **Ctrl+C** in each server terminal. If a port is already in use, first check whether an earlier instance is still running; avoid starting duplicate servers on ports 8000 or 8001.

## 5. Connect an MCP client

Configure an MCP-compatible client with:

```text
http://127.0.0.1:8001/mcp
```

Start the Streamable HTTP server before attempting to connect. The project's `.vscode/mcp.json` includes an HTTP configuration and an optional stdio configuration. The HTTP server is not automatically launched by the web app.

For a client that launches a local MCP subprocess, set `MCP_TRANSPORT=stdio` in its process environment. The repository's stdio configuration launches the virtual-environment Python interpreter with `python -m app.mcp_server`. Keep stdio dedicated to the MCP protocol; do not treat it as a browser-accessible service.

For complete tool descriptions and per-tool behavior, see [docs/MCP.md](docs/MCP.md). It lists the 41 tools and documents both resources, the prompt, test coverage, and security boundaries.

### MCP capabilities

- **Planning:** task listing/details/create/status update; daily plan.
- **Inbox:** sample message search/details/action extraction; local reply drafts.
- **Meals and shopping:** sample ingredients/preferences; meal suggestions; saved plans and shopping lists.
- **Finance:** sample expenses and bills; keyword categorization; budget summaries.
- **Travel:** sample trips, estimates and checklists; pending trip-change approvals and resolution.
- **Family:** sample appointments/conflict checks; local appointment/reminder creation; preparation tasks and unsent check-in drafts.
- **Business:** sample business summary, inventory and orders; unsent customer follow-up drafts.
- **Accessibility:** simplify instructions, create task checklists, reformat plans, summarize workflow results.

Resources:

- `one-request://agents/catalog` describes the specialist capabilities and demo data mode.
- `one-request://demo/data-boundaries` explains what the server does and does not connect to.

Prompt:

- `coordinate_workflow(request)` guides the client to select relevant specialists, respect dependencies, verify results, disclose sample data, and not claim unperformed external actions.

## 6. REST API overview

The REST API is separate from the MCP protocol endpoint. Use `/docs` for the generated OpenAPI schema and request forms.

| Method and path | Purpose |
| --- | --- |
| `GET /health` | Process liveness. |
| `GET /ready` | Database readiness. |
| `GET /api/v1/runtime` | Reports offline or ADK mode. |
| `GET /api/v1/agents` | Lists the eight specialist capabilities. |
| `GET /api/v1/agents/{agent_id}` | Retrieves one capability. |
| `POST /api/v1/agents/{agent_id}/run` | Runs one specialist against a request. |
| `POST /api/v1/workflows` | Coordinates one workflow request. |
| `GET /api/v1/workflows/{workflow_id}` | Retrieves the workflow, response, agent results, and events. |
| `GET /api/v1/workflows/{workflow_id}/events` | Retrieves the workflow event trace. |
| `GET /api/v1/tasks` | Lists tasks; supports status, offset, and limit query parameters. |
| `GET /api/v1/tasks/daily-plan` | Prioritizes local tasks for an optional ISO date. |
| `GET /api/v1/tasks/{task_id}` | Retrieves a task. |
| `POST /api/v1/tasks` | Creates a local task. |
| `PATCH /api/v1/tasks/{task_id}` | Updates a local task status. |
| `POST /api/v1/tasks/checklist` | Builds a checklist from task IDs. |
| `GET /api/v1/expenses` | Lists sample expenses; optional category filter. |
| `GET /api/v1/bills` | Lists sample bills. |
| `GET /api/v1/budget/summary` | Computes a sample budget summary. |
| `GET /api/v1/messages` | Searches sample inbox messages. |
| `GET /api/v1/messages/{message_id}` | Retrieves a sample message. |
| `GET /api/v1/messages/{message_id}/action-items` | Extracts possible message actions. |
| `POST /api/v1/messages/{message_id}/draft-reply` | Stores an unsent local reply draft. |
| `GET /api/v1/meals/preferences` | Retrieves local meal preferences. |
| `GET /api/v1/meals/ingredients` | Lists sample ingredients. |
| `POST /api/v1/meals/plan` | Suggests meals under an optional budget. |
| `POST /api/v1/meals/plans` | Saves a plan and its local shopping list. |
| `GET /api/v1/meals/shopping-list` | Retrieves saved shopping-list items. |
| `GET /api/v1/trips` | Lists sample itineraries. |
| `GET /api/v1/trips/{trip_id}` | Retrieves one sample itinerary. |
| `GET /api/v1/trips/{trip_id}/checklist` | Retrieves preparation suggestions. |
| `POST /api/v1/trips/{trip_id}/change-requests` | Creates a pending local trip-change request. |
| `GET /api/v1/approvals` | Lists local approval requests. |
| `POST /api/v1/approvals/{approval_id}/decision` | Approves or rejects a pending local change. |
| `POST /api/v1/trips/estimate` | Checks a supplied estimate against sample budget data. |
| `GET /api/v1/appointments` | Lists sample appointments. |
| `GET /api/v1/appointments/conflicts` | Checks sample appointments for overlaps. |
| `POST /api/v1/appointments` | Creates a local appointment record. |
| `POST /api/v1/appointments/{appointment_id}/checkin-drafts` | Stores an unsent local family check-in draft. |
| `GET /api/v1/appointments/checkin-drafts` | Lists local family check-in drafts. |
| `GET /api/v1/reminders` | Lists local reminders. |
| `POST /api/v1/reminders` | Stores a reminder; does not deliver a notification. |
| `GET /api/v1/inventory` | Lists sample inventory. |
| `GET /api/v1/orders` | Lists sample orders. |
| `GET /api/v1/business/summary` | Summarizes sample business records. |
| `POST /api/v1/orders/{order_id}/followup-drafts` | Stores an unsent customer follow-up draft. |
| `GET /api/v1/orders/followup-drafts` | Lists local customer follow-up drafts. |
| `GET /openapi.json` | Retrieves the OpenAPI schema. |

The MCP endpoint is `http://127.0.0.1:8001/mcp` and is not a REST route.

### Example workflow request from PowerShell

With the API running:

```powershell
$body = @{ request = "Prepare my trip, check the budget, and organize my tasks." } | ConvertTo-Json
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/workflows `
  -ContentType "application/json" `
  -Body $body
```

The response includes the workflow ID, mode, status, final response, agent results, and trace events. Query the workflow later at `GET /api/v1/workflows/{workflow_id}`.

## 7. Data persistence and records

`app/models.py` defines SQLAlchemy models; `app/database.py` constructs the engine and session factory; `app/services.py` seeds initial sample data and contains domain operations. `app/main.py` and `app/mcp_server.py` call the shared service functions rather than maintaining separate copies of domain state.

By default, the SQLite file is:

```text
data/one_request_many_actions.db
```

The path is relative to the working directory from which the processes are started. Run both commands from the project root to ensure they use the same database. The database is persistent and can contain locally entered demo records and workflow history. Protect it like other user data and do not publish it.

The schema is created through SQLAlchemy `create_all` on startup. This project currently has **no database migration/versioning system**, so schema-changing upgrades should be planned carefully before reusing important local data. Concurrent first-time initialization is covered by a test.

## 8. Project structure

```text
app/
  adk_runtime.py       Optional Google ADK coordinator and specialist agents
  config.py            Environment and .env configuration
  database.py          SQLAlchemy engine, Base, and session factory
  main.py              FastAPI routes and static web app
  mcp_client.py        MCP Streamable HTTP inspection client
  mcp_server.py        MCP tools, resources, prompt, and transport launcher
  models.py            SQLite persistence models
  orchestrator.py      Domain selection, dependencies, workflow trace
  schemas.py           Pydantic API request and response models
  services.py          Seed data and shared domain operations
  static/              HTML, CSS, and JavaScript browser UI
docs/
  MCP.md               MCP inventory and operator/security guide
skills/
  one-request-many-actions/
    SKILL.md           Portable agent instructions
tests/
  test_api.py          API, workflow, persistence, and ADK setup tests
  test_database_init.py Concurrent database initialization regression test
  test_mcp.py          Real MCP protocol discovery and invocation test
data/
  one_request_many_actions.db  Default local database, generated at runtime
.vscode/
  mcp.json             VS Code HTTP and stdio MCP server configurations
.env.example           Configuration template
pyproject.toml         Dependencies, entry points, and tooling configuration
README.md              Short project overview and quick start
SUBMISSION.md          Hackathon submission draft
PROJECT_GUIDE.md       This end-to-end project guide
```

## 9. Tests and code checks

Run these from the project root with the project virtual environment active:

```powershell
python -m pytest -q
python -m ruff check app tests
python -m compileall -q app tests
node --check app\static\app.js
```

The test suite covers API health and readiness, workflow selection and dependency ordering, API validation and local persistence, explicit trip approval, MCP initialization/discovery/tool invocation/resources/prompts, and concurrent database initialization. The MCP integration test starts a local server on an available loopback port and uses the official SDK client.

## 10. Troubleshooting

### `GET /` on port 8001 returns 404

That is expected. Port 8001 is the MCP server and does not host the browser UI. Open the UI at `http://127.0.0.1:8000`. Configure an MCP client with `http://127.0.0.1:8001/mcp`, not `/`.

### MCP client cannot connect

1. Confirm the MCP terminal shows the Uvicorn server listening on `127.0.0.1:8001`.
2. Confirm `MCP_TRANSPORT=streamable-http`.
3. Confirm the client URL ends in `/mcp`.
4. Run `python -m app.mcp_client --call-budget` from the project root.
5. Ensure the service is not already running on another port and the client uses that port.

### Browser app is unavailable

Confirm the web terminal is running on port 8000, then check `http://127.0.0.1:8000/ready`. The app and MCP services are separate and must each be started.

### Port 8000 or 8001 is already in use

An earlier instance may still be running. Stop it with Ctrl+C in its terminal before launching another copy. If you intentionally change a port, update the app/MCP configuration and any client URL consistently.

### ADK reports a missing key or MCP connection

Use `$env:AGENT_MODE = "demo"` to run without credentials. ADK mode requires a valid `GOOGLE_API_KEY` and a reachable MCP Streamable HTTP server at `MCP_SERVER_URL`.

### Module import or package errors

From the project root, activate `.venv` and run `python -m pip install -e ".[dev]"`. Confirm `python --version` is 3.11 or later and that the active interpreter is `.venv\Scripts\python.exe`.

### MCP endpoint appears broken in a browser

MCP is a protocol, not an HTML webpage. Use an MCP client or `python -m app.mcp_client`; do not judge the protocol by opening its endpoint as a regular web page.

## 11. Security and production readiness

This is a local development/hackathon demo, not a hardened public service.

- Both the FastAPI REST API and MCP server are unauthenticated.
- MCP Streamable HTTP is restricted to loopback by a host check, but that is not authentication or production protection.
- Do not bind services to public interfaces, expose ports through a tunnel, or deploy them publicly as-is.
- The SQLite database may contain user-created local records; protect and back it up appropriately.
- Never put API keys in source code, `.vscode/mcp.json`, screenshots, or submission materials.
- Before remote deployment, implement and review authentication, authorization, TLS, origin/DNS-rebinding protections, rate limiting, privacy and retention controls, secure secret handling, and deployment monitoring.
- Any future real provider integrations must separately address permissions, consent, retries, idempotency, auditability, error handling, and explicit approval for consequential actions.

## 12. What remains beyond the hackathon demo

The local coding project is end-to-end as a simulated assistant: the user can submit a request, see coordinated specialist output, inspect the trace, use the REST API, and connect an MCP client. It is suitable for demonstrating the Alexa+ track's requested MCP, Agent Skill, and Streamable HTTP concepts.

It is **not** yet a real-world personal assistant connected to user accounts. The following are not implemented:

- Real inbox, email sending, calendar sync, travel booking, bank/account access, commerce, or notification providers.
- Live inventory, real pantry quantities, real prices, or external shopping lists.
- Production authentication, hosted deployment, multi-user isolation, or a migration system.
- Verified live Gemini execution without the user's key and provider access.
- A recorded product demo or an actual Devpost submission; those are presenter/submission steps.

To move toward a real provider-connected product, add provider adapters one domain at a time, start with read-only access and least-privilege scopes, test with sandbox accounts, then add carefully reviewed write actions with explicit user approval and auditable outcomes. Do not represent the current sample-data implementation as connected to real services.

## 13. Related project documents

- [README.md](README.md) — overview and quick start.
- [docs/MCP.md](docs/MCP.md) — complete MCP tool inventory and MCP-specific setup.
- [skills/one-request-many-actions/SKILL.md](skills/one-request-many-actions/SKILL.md) — portable specialist coordination and safety instructions.
- [SUBMISSION.md](SUBMISSION.md) — hackathon submission draft and scope statement.
