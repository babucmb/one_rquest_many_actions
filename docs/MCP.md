# MCP implementation and operator guide

## Implemented MCP surface

The project uses the official Python MCP SDK (`mcp==1.30.0`) and exposes MCP separately from its FastAPI REST API. The default protocol transport is **Streamable HTTP**, mounted at `http://127.0.0.1:8001/mcp`. The server supports MCP initialization, capability discovery, tool listing and calls, resource listing and reads, prompt listing and retrieval, and protocol-level tool errors.

### Tools

All writes affect only the local SQLite demo database. No tool is connected to a real service.

| Domain | MCP tool | Purpose |
| --- | --- | --- |
| Planning | `list_tasks_tool` | List tasks, optionally by status |
| Planning | `get_task_details_tool` | Retrieve one task by ID |
| Planning | `create_task_tool` | Create a local task |
| Planning | `update_task_status_tool` | Change a task to pending, in progress, or done |
| Planning | `get_daily_plan_tool` | Prioritize tasks and identify due/overdue tasks for an ISO date |
| Inbox | `search_demo_messages_tool` | Search seeded inbox messages |
| Inbox | `get_message_details_tool` | Retrieve one seeded message |
| Inbox | `extract_message_action_items_tool` | Detect a possible request in a message; deadline needs verification |
| Inbox | `create_reply_draft_tool` | Save a reply draft locally; never sends |
| Meals | `get_ingredients_tool` | List sample pantry ingredients |
| Meals | `get_meal_preferences_tool` | Read local meal preferences |
| Meals | `get_meal_plan_tool` | Suggest meals within an optional illustrative budget |
| Meals | `save_meal_plan_tool` | Persist a meal plan and local shopping-list items |
| Meals | `get_shopping_list_tool` | Read saved shopping-list items |
| Finance | `list_expenses_tool` | Read seeded expenses, optionally by category |
| Finance | `list_bills_tool` | Read sample bills; no payment operation |
| Finance | `categorize_expenses_tool` | Apply documented keyword categories to demo expenses |
| Finance | `get_budget_summary_tool` | Calculate expense, upcoming-bill, and estimate totals |
| Travel | `get_trip_summary_tool` | Read sample itinerary records |
| Travel | `estimate_trip_cost_tool` | Compare the sample trip estimate with demo budget data |
| Travel | `get_travel_checklist_tool` | Return suggested preparation steps |
| Travel | `request_trip_update_approval_tool` | Create a pending local change request without applying it |
| Travel | `list_pending_approvals_tool` | Review approval records |
| Travel | `resolve_trip_update_approval_tool` | Apply/reject a pending local trip update after an explicit decision |
| Family | `get_appointments_tool` | Read sample appointments |
| Family | `check_appointment_conflicts_tool` | Find overlaps assuming one-hour appointment blocks |
| Family | `create_appointment_tool` | Add a local appointment; does not sync a calendar |
| Family | `create_reminder_tool` | Store a local reminder; does not deliver a notification |
| Family | `list_reminders_tool` | List local reminder records |
| Family | `create_appointment_preparation_task_tool` | Create a local task for an appointment |
| Family | `create_family_checkin_draft_tool` | Save an unsent check-in draft |
| Family | `list_family_checkin_drafts_tool` | List unsent local check-in drafts |
| Business | `get_business_summary_tool` | Summarize seeded inventory and order records |
| Business | `list_inventory_tool` | Read sample inventory and reorder thresholds |
| Business | `list_orders_tool` | Read sample orders |
| Business | `create_customer_followup_draft_tool` | Save a customer follow-up draft; never sends |
| Business | `list_customer_followup_drafts_tool` | List unsent local customer drafts |
| Accessibility | `simplify_instructions_tool` | Turn supplied instructions into numbered steps |
| Accessibility | `create_task_checklist_tool` | Format task IDs into steps and report missing IDs |
| Accessibility | `reformat_plan_tool` | Format supplied steps as numbers, bullets, or a concise line |
| Accessibility | `summarize_workflow_results_tool` | Retrieve a stored workflow summary and specialist results |

### Resources and prompt

- `one-request://agents/catalog` — the eight agent capabilities and demo mode.
- `one-request://demo/data-boundaries` — local data and external-action limitations.
- `coordinate_workflow(request)` — instructions for selecting agents, honoring dependencies, checking results, and disclosing demo data.

## Start and connect

### Streamable HTTP (hackathon path)

In the project directory, activate the virtual environment and start the server:

```powershell
.\.venv\Scripts\Activate.ps1
$env:MCP_TRANSPORT = "streamable-http"
python -m app.mcp_server
```

Configure a client to `http://127.0.0.1:8001/mcp`. The repository includes both HTTP and optional stdio entries in `.vscode/mcp.json`. The HTTP entry connects to this server; start it separately before connecting.

### Optional stdio client

For clients that launch MCP servers as subprocesses, start a server over stdio:

```powershell
$env:MCP_TRANSPORT = "stdio"
python -m app.mcp_server
```

Do not run that command in the same terminal as a user-facing interactive shell; stdio is reserved for the MCP client's protocol stream.

### Inspect using the included client

With the Streamable HTTP server running in another terminal:

```powershell
python -m app.mcp_client
python -m app.mcp_client --call-budget
```

The client initializes a real MCP session and prints the server identity, available tools, resources, and prompts. `--call-budget` also invokes the budget tool.

## Tests

`tests/test_mcp.py` starts the official SDK server on an unused loopback port, uses `ClientSession` with `streamable_http_client`, and verifies discovery and invocation across the domain tools, prompt and resources, validation failures, local persistence, and explicit trip-approval behavior. It also verifies that a proposed itinerary edit does not change trip data until approved.

Run:

```powershell
python -m pytest tests/test_mcp.py -q
```

## Security and deployment boundary

The MCP service refuses non-loopback Streamable HTTP binding. This protects a development demo; it is **not** production authentication. Do not expose the service, the REST API, or the SQLite database publicly. Remote deployment needs a separately reviewed authentication/authorization gateway, TLS, origin and DNS-rebinding protections, rate limiting, privacy controls, and deployment operations. Do not put secrets in the checked-in VS Code MCP config.

