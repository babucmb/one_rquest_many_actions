---
name: one-request-many-actions
description: Coordinate planning, inbox follow-ups, meals, budgets, travel, business operations, family appointments, and accessible checklists using the One Request, Many Actions MCP server.
---

# One Request, Many Actions

Use this skill when a user has a goal spanning one or more supported workflow domains. The MCP server exposes typed tools, an agent catalog resource, a data-boundaries resource, and the `coordinate_workflow` prompt.

## Workflow

1. Restate the user's goal and ask for a missing essential detail.
2. Select only relevant specialists. Plan dependencies before execution.
3. Use MCP tools for local data retrieval, deterministic calculations, and explicitly requested local record changes.
4. Run independent read-only calls concurrently when safe. Pass verified values to dependent tools.
5. Present facts, estimates, suggestions, pending approvals, and local changes separately.
6. Report failed or missing results; do not claim a tool succeeded if it returned an error.

## Domain tools

- **Planning:** `list_tasks_tool`, `get_task_details_tool`, `create_task_tool`, `update_task_status_tool`, `get_daily_plan_tool`
- **Inbox:** `search_demo_messages_tool`, `get_message_details_tool`, `extract_message_action_items_tool`, `create_reply_draft_tool`
- **Meals and shopping:** `get_ingredients_tool`, `get_meal_preferences_tool`, `get_meal_plan_tool`, `save_meal_plan_tool`, `get_shopping_list_tool`
- **Budget:** `list_expenses_tool`, `list_bills_tool`, `categorize_expenses_tool`, `get_budget_summary_tool`
- **Travel:** `get_trip_summary_tool`, `estimate_trip_cost_tool`, `get_travel_checklist_tool`, `request_trip_update_approval_tool`, `list_pending_approvals_tool`, `resolve_trip_update_approval_tool`
- **Family:** `get_appointments_tool`, `check_appointment_conflicts_tool`, `create_appointment_tool`, `create_reminder_tool`, `list_reminders_tool`, `create_appointment_preparation_task_tool`, `create_family_checkin_draft_tool`, `list_family_checkin_drafts_tool`
- **Business:** `get_business_summary_tool`, `list_inventory_tool`, `list_orders_tool`, `create_customer_followup_draft_tool`, `list_customer_followup_drafts_tool`
- **Accessible tasks:** `simplify_instructions_tool`, `create_task_checklist_tool`, `reformat_plan_tool`, `summarize_workflow_results_tool`

## Dependencies and approval

- Check a trip estimate before evaluating it against the sample budget.
- Check available funds before using them as a meal-plan budget.
- Complete source-data checks before producing a final preparation checklist.
- `request_trip_update_approval_tool` creates a pending request and does **not** change trip data. Show the requested change to the user; call `resolve_trip_update_approval_tool` with `approved=true` only after an explicit user decision. A rejection is recorded without changing the trip.
- A saved meal plan, task, appointment, reminder, or message draft is a local SQLite change. Do not create one unless it supports the user's request.

## Trust and data boundaries

All connected data is seeded or user-entered local demo data. Price figures are illustrative. No real email, bank, calendar, travel, store, or notification provider is connected. Never claim that an email was sent, money moved, a bill paid, a purchase or booking made, a live calendar changed, or a reminder delivered. Reminders and communications remain local drafts.

