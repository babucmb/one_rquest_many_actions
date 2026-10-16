from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine
from app.models import (
    Appointment,
    ApprovalRequest,
    Bill,
    CustomerFollowupDraft,
    Expense,
    FamilyCheckinDraft,
    InventoryItem,
    MealPlanRecord,
    Message,
    Order,
    Reminder,
    ShoppingListItem,
    Task,
    Trip,
    UserPreference,
)

AGENTS = [
    {
        "id": "planning",
        "name": "Everyday Planner",
        "description": "Turns goals and deadlines into a prioritized, trackable plan.",
        "capability": "tasks, priorities, preparation checklists",
    },
    {
        "id": "inbox",
        "name": "Inbox-to-Action",
        "description": "Finds follow-ups in the included sample inbox and prepares drafts.",
        "capability": "sample messages, action items, reply drafts",
    },
    {
        "id": "meals",
        "name": "Meal & Shopping",
        "description": "Suggests practical meals and estimates a shopping list.",
        "capability": "meal ideas, sample pantry, estimated shopping costs",
    },
    {
        "id": "finance",
        "name": "Budget Organizer",
        "description": "Summarizes sample expenses and checks estimates against a budget.",
        "capability": "sample expenses, bills, deterministic budget math",
    },
    {
        "id": "travel",
        "name": "Travel Coordinator",
        "description": "Reviews sample itinerary data and prepares a travel checklist.",
        "capability": "sample trip, estimate review, preparation checklist",
    },
    {
        "id": "business",
        "name": "Business Operations",
        "description": "Highlights sample inventory risks and pending customer orders.",
        "capability": "sample inventory, orders, follow-up drafts",
    },
    {
        "id": "family",
        "name": "Family Coordinator",
        "description": "Reviews sample appointments and highlights time conflicts.",
        "capability": "sample appointments, conflict review, reminders",
    },
    {
        "id": "accessibility",
        "name": "Clear Steps",
        "description": "Rewrites a complex request as a short, sequential checklist.",
        "capability": "plain-language summaries, step-by-step checklists",
    },
]

MONTHLY_BUDGET = 2500.0
PANTRY = ["rice", "eggs", "spinach", "tomatoes", "lentils"]
MEAL_IDEAS = [
    {
        "name": "Tomato and lentil rice bowls",
        "estimated_cost": 8.5,
        "uses": ["rice", "tomatoes", "lentils", "olive oil"],
    },
    {
        "name": "Spinach and egg fried rice",
        "estimated_cost": 6.0,
        "uses": ["rice", "eggs", "spinach", "green onion"],
    },
]


def initialize_database() -> None:
    with engine.connect() as connection, Session(bind=connection) as db:
        if engine.dialect.name == "sqlite":
            connection.exec_driver_sql("BEGIN IMMEDIATE")
        Base.metadata.create_all(bind=connection)
        today = date.today()
        if db.scalar(select(Task.id).limit(1)) is None:
            db.add_all(
                [
                    Task(
                        title="Confirm travel documents",
                        due_date=str(today + timedelta(days=1)),
                        priority="high",
                    ),
                    Task(
                        title="Pick up groceries",
                        due_date=str(today + timedelta(days=2)),
                        priority="normal",
                    ),
                    Task(
                        title="Review monthly budget",
                        due_date=str(today + timedelta(days=3)),
                        priority="low",
                    ),
                ]
            )
        if db.scalar(select(Expense.id).limit(1)) is None:
            db.add_all(
                [
                    Expense(
                        description="Weekly groceries",
                        category="Food",
                        amount=84.35,
                        recorded_on=str(today),
                    ),
                    Expense(
                        description="Local transit",
                        category="Transport",
                        amount=32.00,
                        recorded_on=str(today),
                    ),
                    Expense(
                        description="Internet service",
                        category="Bills",
                        amount=59.99,
                        recorded_on=str(today),
                    ),
                ]
            )
        if db.scalar(select(Bill.id).limit(1)) is None:
            db.add_all(
                [
                    Bill(name="Electricity", amount=74.25, due_date=str(today + timedelta(days=4))),
                    Bill(name="Internet", amount=59.99, due_date=str(today + timedelta(days=8))),
                ]
            )
        if db.scalar(select(Message.id).limit(1)) is None:
            db.add_all(
                [
                    Message(
                        sender="Jordan Lee",
                        subject="Project review — Friday",
                        body=(
                            "Could you review the shared project notes before Friday "
                            "and send me your feedback?"
                        ),
                        received_at=str(today),
                    ),
                    Message(
                        sender="Community Center",
                        subject="Volunteer orientation",
                        body=(
                            "Please confirm whether you can attend the orientation next Wednesday."
                        ),
                        received_at=str(today),
                    ),
                ]
            )
        if db.scalar(select(Trip.id).limit(1)) is None:
            db.add(
                Trip(
                    destination="Portland",
                    starts_on=str(today + timedelta(days=10)),
                    ends_on=str(today + timedelta(days=12)),
                    estimated_cost=420.0,
                    notes="Sample itinerary only; no booking or live travel provider is connected.",
                )
            )
        if db.scalar(select(Appointment.id).limit(1)) is None:
            tomorrow = today + timedelta(days=1)
            db.add_all(
                [
                    Appointment(
                        title="Dentist check-up",
                        starts_at=f"{tomorrow}T09:00:00",
                        owner="You",
                        notes="Sample appointment",
                    ),
                    Appointment(
                        title="School pickup",
                        starts_at=f"{tomorrow}T15:00:00",
                        owner="Family",
                        notes="Sample appointment",
                    ),
                ]
            )
        if db.scalar(select(InventoryItem.id).limit(1)) is None:
            db.add_all(
                [
                    InventoryItem(name="Shipping boxes", quantity=8, reorder_at=12),
                    InventoryItem(name="Thermal labels", quantity=36, reorder_at=20),
                    InventoryItem(name="Packing tape", quantity=5, reorder_at=10),
                ]
            )
        if db.scalar(select(Order.id).limit(1)) is None:
            db.add_all(
                [
                    Order(
                        customer="Northwind Studio",
                        status="awaiting follow-up",
                        due_date=str(today + timedelta(days=1)),
                    ),
                    Order(
                        customer="Mosaic Goods",
                        status="processing",
                        due_date=str(today + timedelta(days=3)),
                    ),
                ]
            )
        if db.get(UserPreference, "meal_preferences") is None:
            db.add(UserPreference(key="meal_preferences", value={"dietary_preferences": []}))
        db.commit()
        connection.commit()


def _dict(row: Any) -> dict[str, Any]:
    return {column.name: getattr(row, column.name) for column in row.__table__.columns}


def list_tasks(status: str | None = None) -> list[dict[str, Any]]:
    with SessionLocal() as db:
        statement = select(Task).order_by(Task.due_date, Task.priority)
        if status:
            statement = statement.where(Task.status == status)
        return [_dict(row) for row in db.scalars(statement)]


def get_task(task_id: str) -> dict[str, Any] | None:
    with SessionLocal() as db:
        task = db.get(Task, task_id)
        return _dict(task) if task else None


def create_task(
    title: str, due_date: str | None = None, priority: str = "normal"
) -> dict[str, Any]:
    with SessionLocal() as db:
        task = Task(title=title, due_date=due_date, priority=priority, source="assistant")
        db.add(task)
        db.commit()
        db.refresh(task)
        return _dict(task)


def daily_plan(for_date: str | None = None) -> dict[str, Any]:
    selected_date = date.fromisoformat(for_date) if for_date else date.today()
    tasks = list_tasks()
    rank = {"high": 0, "normal": 1, "low": 2}
    tasks.sort(key=lambda task: (rank.get(task["priority"], 1), task["due_date"] or "9999-12-31"))
    due = [
        task
        for task in tasks
        if task["status"] != "done"
        and task["due_date"]
        and date.fromisoformat(task["due_date"][:10]) <= selected_date
    ]
    return {
        "date": str(selected_date),
        "data_source": "local_demo_tasks",
        "prioritized_tasks": [task for task in tasks if task["status"] != "done"],
        "due_or_overdue": due,
        "note": (
            "Suggested order is based on priority and due date; "
            "no calendar availability is connected."
        ),
    }


def update_task_status(task_id: str, status: str) -> dict[str, Any] | None:
    with SessionLocal() as db:
        task = db.get(Task, task_id)
        if task is None:
            return None
        task.status = status
        db.commit()
        db.refresh(task)
        return _dict(task)


def list_expenses(category: str | None = None) -> list[dict[str, Any]]:
    with SessionLocal() as db:
        statement = select(Expense).order_by(Expense.recorded_on.desc())
        if category:
            statement = statement.where(Expense.category == category)
        return [_dict(row) for row in db.scalars(statement)]


def list_bills() -> list[dict[str, Any]]:
    with SessionLocal() as db:
        return [_dict(row) for row in db.scalars(select(Bill).order_by(Bill.due_date))]


def budget_summary(additional_estimate: float = 0) -> dict[str, Any]:
    with SessionLocal() as db:
        expenses = list(db.scalars(select(Expense)))
        bills = list(db.scalars(select(Bill).where(Bill.status == "upcoming")))
    spent = round(sum(item.amount for item in expenses), 2)
    bills_due = round(sum(item.amount for item in bills), 2)
    available = round(MONTHLY_BUDGET - spent - bills_due, 2)
    remaining_after_estimate = round(available - additional_estimate, 2)
    return {
        "data_source": "seeded_demo_records",
        "monthly_budget": MONTHLY_BUDGET,
        "recorded_expenses": spent,
        "upcoming_bills": bills_due,
        "available_before_new_estimate": available,
        "additional_estimate": round(additional_estimate, 2),
        "available_after_estimate": remaining_after_estimate,
        "within_available_budget": remaining_after_estimate >= 0,
        "bills": [_dict(item) for item in bills],
    }


def categorize_expenses() -> dict[str, Any]:
    rules = {
        "Food": ("grocery", "restaurant", "food", "meal"),
        "Transport": ("transit", "taxi", "fuel", "bus", "train"),
        "Bills": ("internet", "electric", "water", "bill", "utility"),
    }
    updated: list[dict[str, Any]] = []
    with SessionLocal() as db:
        expenses = list(db.scalars(select(Expense)))
        for expense in expenses:
            description = expense.description.casefold()
            category = next(
                (
                    label
                    for label, terms in rules.items()
                    if any(term in description for term in terms)
                ),
                expense.category,
            )
            expense.category = category
            updated.append(_dict(expense))
        db.commit()
    return {"data_source": "seeded_demo_records", "categorized_expenses": updated}


def list_messages(query: str = "") -> list[dict[str, Any]]:
    with SessionLocal() as db:
        rows = list(db.scalars(select(Message).order_by(Message.received_at.desc())))
    needle = query.casefold().strip()
    if needle:
        rows = [
            row
            for row in rows
            if needle in row.subject.casefold()
            or needle in row.body.casefold()
            or needle in row.sender.casefold()
        ]
    return [_dict(row) for row in rows]


def get_message(message_id: str) -> dict[str, Any] | None:
    with SessionLocal() as db:
        message = db.get(Message, message_id)
        return _dict(message) if message else None


def extract_message_actions(message_id: str) -> dict[str, Any] | None:
    message = get_message(message_id)
    if message is None:
        return None
    body = message["body"]
    action_markers = ("please", "could you", "can you", "need to", "remember to")
    has_action = any(marker in body.casefold() for marker in action_markers)
    return {
        "message_id": message_id,
        "subject": message["subject"],
        "action_items": [body] if has_action else [],
        "deadline": None,
        "deadline_note": "No structured deadline was extracted; review the message text.",
        "source": "sample_inbox",
    }


def save_reply_draft(message_id: str, reply_text: str) -> dict[str, Any] | None:
    with SessionLocal() as db:
        message = db.get(Message, message_id)
        if message is None:
            return None
        message.reply_draft = reply_text
        db.commit()
        db.refresh(message)
        return _dict(message)


def meal_plan(budget: float | None = None) -> dict[str, Any]:
    meals = [meal for meal in MEAL_IDEAS if budget is None or meal["estimated_cost"] <= budget]
    total = round(sum(meal["estimated_cost"] for meal in meals), 2)
    needed = sorted(
        {ingredient for meal in meals for ingredient in meal["uses"] if ingredient not in PANTRY}
    )
    return {
        "data_source": "sample_pantry_and_estimates",
        "available_ingredients": PANTRY,
        "meals": meals,
        "estimated_total": total,
        "shopping_list": needed,
        "budget_constraint": budget,
        "price_note": (
            "Illustrative estimates only; no live store pricing or ordering is connected."
        ),
    }


def list_ingredients() -> dict[str, Any]:
    return {
        "data_source": "sample_pantry",
        "ingredients": [
            {"name": item, "quantity": "available", "unit": "sample"} for item in PANTRY
        ],
    }


def meal_preferences() -> dict[str, Any]:
    with SessionLocal() as db:
        preference = db.get(UserPreference, "meal_preferences")
        return preference.value if preference else {"dietary_preferences": []}


def save_meal_plan(name: str, budget: float | None = None) -> dict[str, Any]:
    plan = meal_plan(budget)
    with SessionLocal() as db:
        record = MealPlanRecord(
            name=name,
            plan=plan,
            estimated_total=plan["estimated_total"],
        )
        db.add(record)
        db.flush()
        for ingredient in plan["shopping_list"]:
            db.add(
                ShoppingListItem(
                    list_id=record.id,
                    ingredient=ingredient,
                    quantity="1",
                    estimated_cost=None,
                )
            )
        db.commit()
        db.refresh(record)
        return {
            "id": record.id,
            "name": record.name,
            "plan": record.plan,
            "estimated_total": record.estimated_total,
            "data_source": record.data_source,
            "shopping_list": shopping_list(record.id),
        }


def shopping_list(list_id: str | None = None) -> list[dict[str, Any]]:
    with SessionLocal() as db:
        statement = select(ShoppingListItem).order_by(ShoppingListItem.ingredient)
        if list_id:
            statement = statement.where(ShoppingListItem.list_id == list_id)
        return [_dict(item) for item in db.scalars(statement)]


def get_trip(trip_id: str | None = None) -> dict[str, Any] | None:
    with SessionLocal() as db:
        if trip_id:
            trip = db.get(Trip, trip_id)
        else:
            trip = db.scalar(select(Trip).order_by(Trip.starts_on))
        return _dict(trip) if trip else None


def request_trip_update_approval(
    trip_id: str,
    destination: str | None = None,
    starts_on: str | None = None,
    ends_on: str | None = None,
    estimated_cost: float | None = None,
) -> dict[str, Any] | None:
    from math import isfinite

    updates = {
        key: value
        for key, value in {
            "destination": destination.strip() if destination else None,
            "starts_on": starts_on,
            "ends_on": ends_on,
            "estimated_cost": estimated_cost,
        }.items()
        if value is not None
    }
    if not updates or ("destination" in updates and not updates["destination"]):
        raise ValueError("Provide at least one non-empty trip field to change.")
    if "starts_on" in updates:
        updates["starts_on"] = str(date.fromisoformat(updates["starts_on"]))
    if "ends_on" in updates:
        updates["ends_on"] = str(date.fromisoformat(updates["ends_on"]))
    if "estimated_cost" in updates and (
        not isfinite(updates["estimated_cost"]) or updates["estimated_cost"] < 0
    ):
        raise ValueError("estimated_cost must be a finite non-negative amount.")
    with SessionLocal() as db:
        trip = db.get(Trip, trip_id)
        if trip is None:
            return None
        updated = {
            "destination": updates.get("destination", trip.destination),
            "starts_on": updates.get("starts_on", trip.starts_on),
            "ends_on": updates.get("ends_on", trip.ends_on),
            "estimated_cost": updates.get("estimated_cost", trip.estimated_cost),
        }
        if date.fromisoformat(updated["ends_on"]) < date.fromisoformat(updated["starts_on"]):
            raise ValueError("trip end date cannot be earlier than its start date.")
        approval = ApprovalRequest(
            action="update_local_trip",
            description=f"Update the local demo trip: {updated['destination']}, "
            f"{updated['starts_on']} to {updated['ends_on']}, estimated "
            f"${updated['estimated_cost']:.2f}.",
            payload={"trip_id": trip_id, "updates": updates},
        )
        db.add(approval)
        db.commit()
        db.refresh(approval)
        result = _dict(approval)
    result["status"] = "awaiting_explicit_approval"
    return result


def resolve_trip_update_approval(approval_id: str, approved: bool) -> dict[str, Any] | None:
    with SessionLocal() as db:
        approval = db.get(ApprovalRequest, approval_id)
        if approval is None:
            return None
        if approval.action != "update_local_trip":
            raise ValueError("approval request has an unsupported action.")
        if approval.approved is not None:
            raise ValueError("approval request was already resolved.")
        approval.approved = approved
        updated_trip = None
        if approved:
            trip = db.get(Trip, approval.payload["trip_id"])
            if trip is None:
                raise ValueError("the trip associated with this approval no longer exists.")
            for field, value in approval.payload["updates"].items():
                setattr(trip, field, value)
            updated_trip = _dict(trip)
        db.commit()
        db.refresh(approval)
        result = _dict(approval)
    result["status"] = "approved" if approved else "rejected"
    if updated_trip is not None:
        result["updated_trip"] = updated_trip
    return result


def list_approval_requests() -> list[dict[str, Any]]:
    with SessionLocal() as db:
        return [
            _dict(item)
            for item in db.scalars(
                select(ApprovalRequest).order_by(ApprovalRequest.created_at.desc())
            )
        ]


def travel_checklist(trip_id: str | None = None) -> dict[str, Any]:
    trip = get_trip(trip_id)
    if trip is None:
        return {"trip": None, "checklist": []}
    return {
        "trip": trip,
        "checklist": [
            {"title": "Confirm itinerary details", "status": "suggested"},
            {"title": "Check travel documents", "status": "suggested"},
            {"title": "Pack essentials", "status": "suggested"},
        ],
        "note": "Checklist suggestions only; no booking or external travel changes are made.",
    }


def trip_summary() -> list[dict[str, Any]]:
    with SessionLocal() as db:
        return [_dict(row) for row in db.scalars(select(Trip).order_by(Trip.starts_on))]


def appointments() -> list[dict[str, Any]]:
    with SessionLocal() as db:
        return [
            _dict(row) for row in db.scalars(select(Appointment).order_by(Appointment.starts_at))
        ]


def appointment_conflicts() -> list[dict[str, Any]]:
    items = appointments()
    conflicts = []
    for index, first in enumerate(items):
        first_start = datetime.fromisoformat(first["starts_at"])
        first_end = first_start + timedelta(hours=1)
        for second in items[index + 1 :]:
            second_start = datetime.fromisoformat(second["starts_at"])
            second_end = second_start + timedelta(hours=1)
            if first_start < second_end and second_start < first_end:
                conflicts.append(
                    {
                        "first": first["title"],
                        "second": second["title"],
                        "overlap_minutes": int(
                            (
                                min(first_end, second_end) - max(first_start, second_start)
                            ).total_seconds()
                            / 60
                        ),
                        "assumption": "Appointments are treated as one-hour blocks.",
                    }
                )
    return conflicts


def create_appointment(title: str, starts_at: str, owner: str = "You") -> dict[str, Any]:
    start = datetime.fromisoformat(starts_at)
    if start.tzinfo is None:
        start = start.replace(tzinfo=datetime.now().astimezone().tzinfo)
    appointment = Appointment(
        title=title,
        starts_at=start.isoformat(),
        owner=owner,
        notes="Created in local demo data; not synced to a calendar.",
    )
    with SessionLocal() as db:
        db.add(appointment)
        db.commit()
        db.refresh(appointment)
        return _dict(appointment)


def create_family_checkin_draft(appointment_id: str, message: str) -> dict[str, Any] | None:
    with SessionLocal() as db:
        appointment = db.get(Appointment, appointment_id)
        if appointment is None:
            return None
        draft = FamilyCheckinDraft(appointment_id=appointment_id, message=message)
        db.add(draft)
        db.commit()
        db.refresh(draft)
        result = _dict(draft)
    result["delivery_status"] = "draft_saved_not_sent"
    return result


def list_family_checkin_drafts() -> list[dict[str, Any]]:
    with SessionLocal() as db:
        return [
            _dict(item)
            for item in db.scalars(
                select(FamilyCheckinDraft).order_by(FamilyCheckinDraft.created_at.desc())
            )
        ]


def create_reminder(title: str, remind_at: str, owner: str = "You") -> dict[str, Any]:
    reminder_time = datetime.fromisoformat(remind_at)
    reminder = Reminder(
        title=title,
        remind_at=reminder_time.isoformat(),
        owner=owner,
        source="local_demo",
    )
    with SessionLocal() as db:
        db.add(reminder)
        db.commit()
        db.refresh(reminder)
        result = _dict(reminder)
    result["delivery_status"] = "stored_locally_not_delivered"
    return result


def list_reminders() -> list[dict[str, Any]]:
    with SessionLocal() as db:
        return [_dict(item) for item in db.scalars(select(Reminder).order_by(Reminder.remind_at))]


def create_customer_followup_draft(order_id: str, message: str) -> dict[str, Any] | None:
    with SessionLocal() as db:
        order = db.get(Order, order_id)
        if order is None:
            return None
        draft = CustomerFollowupDraft(
            order_id=order.id,
            customer=order.customer,
            message=message,
        )
        db.add(draft)
        db.commit()
        db.refresh(draft)
        result = _dict(draft)
    result["delivery_status"] = "draft_saved_not_sent"
    return result


def list_customer_followup_drafts() -> list[dict[str, Any]]:
    with SessionLocal() as db:
        return [
            _dict(item)
            for item in db.scalars(
                select(CustomerFollowupDraft).order_by(CustomerFollowupDraft.created_at.desc())
            )
        ]


def business_summary() -> dict[str, Any]:
    with SessionLocal() as db:
        items = list(db.scalars(select(InventoryItem).order_by(InventoryItem.quantity)))
        orders = list(db.scalars(select(Order).order_by(Order.due_date)))
    low_stock = [item for item in items if item.quantity <= item.reorder_at]
    return {
        "data_source": "seeded_demo_records",
        "low_stock": [_dict(item) for item in low_stock],
        "inventory": [_dict(item) for item in items],
        "orders": [_dict(order) for order in orders],
        "external_actions": "No customer messages or orders are sent.",
    }


def list_inventory() -> list[dict[str, Any]]:
    with SessionLocal() as db:
        return [
            _dict(item) for item in db.scalars(select(InventoryItem).order_by(InventoryItem.name))
        ]


def list_orders() -> list[dict[str, Any]]:
    with SessionLocal() as db:
        return [_dict(item) for item in db.scalars(select(Order).order_by(Order.due_date))]


def simplify_instructions(text: str) -> list[str]:
    sentences = [part.strip(" .") for part in text.replace("\n", ". ").split(".") if part.strip()]
    return [f"{index}. {sentence}" for index, sentence in enumerate(sentences, start=1)] or [
        "1. Start by describing the task you want help with."
    ]


def task_checklist(task_ids: list[str]) -> dict[str, Any]:
    with SessionLocal() as db:
        tasks = [db.get(Task, task_id) for task_id in task_ids]
    missing = [task_id for task_id, task in zip(task_ids, tasks, strict=True) if task is None]
    return {
        "steps": [
            {
                "number": index,
                "title": task.title,
                "status": task.status,
                "due_date": task.due_date,
            }
            for index, task in enumerate((task for task in tasks if task is not None), start=1)
        ],
        "missing_task_ids": missing,
    }


def run_specialist(
    agent_id: str, request: str, context: dict[str, Any] | None = None
) -> dict[str, Any]:
    context = context or {}
    if agent_id == "planning":
        tasks = list_tasks()
        return {
            "summary": (
                f"Reviewed {len(tasks)} sample tasks and prepared a prioritized next-step list."
            ),
            "data": {"tasks": tasks, "suggested_next_step": tasks[0] if tasks else None},
            "tool_calls": ["list_tasks"],
        }
    if agent_id == "inbox":
        messages = list_messages()
        follow_ups = [
            item
            for item in messages
            if "please" in item["body"].casefold() or "could you" in item["body"].casefold()
        ]
        return {
            "summary": f"Found {len(follow_ups)} sample messages that appear to need a follow-up.",
            "data": {
                "messages": messages,
                "action_items": [item["subject"] for item in follow_ups],
            },
            "tool_calls": ["search_demo_messages"],
        }
    if agent_id == "meals":
        budget = context.get("available_budget")
        result = meal_plan(float(budget) if budget is not None else None)
        return {
            "summary": (
                f"Suggested {len(result['meals'])} meals; sample shopping estimate is "
                f"${result['estimated_total']:.2f}."
            ),
            "data": result,
            "tool_calls": ["get_meal_plan"],
        }
    if agent_id == "finance":
        estimate = float(context.get("trip_estimate", 0))
        result = budget_summary(estimate)
        return {
            "summary": (
                f"Sample records leave ${result['available_after_estimate']:.2f} "
                "after upcoming bills"
                + (f" and the ${estimate:.2f} trip estimate." if estimate else ".")
            ),
            "data": result,
            "tool_calls": ["get_budget_summary"],
        }
    if agent_id == "travel":
        trips = trip_summary()
        trip = trips[0] if trips else None
        return {
            "summary": (
                f"Reviewed the sample trip to {trip['destination']} with an estimated cost of "
                f"${trip['estimated_cost']:.2f}."
                if trip
                else "No sample trip is available yet."
            ),
            "data": {
                "trips": trips,
                "checklist": [
                    "Confirm itinerary details",
                    "Check travel documents",
                    "Pack essentials",
                ],
            },
            "tool_calls": ["get_trip_summary"],
        }
    if agent_id == "business":
        result = business_summary()
        return {
            "summary": (
                f"{len(result['low_stock'])} sample inventory items are at or below "
                "their reorder threshold."
            ),
            "data": result,
            "tool_calls": ["get_business_summary"],
        }
    if agent_id == "family":
        items = appointments()
        return {
            "summary": f"Reviewed {len(items)} sample appointments and checked for overlaps.",
            "data": {"appointments": items, "conflicts": appointment_conflicts()},
            "tool_calls": ["get_appointments"],
        }
    if agent_id == "accessibility":
        steps = simplify_instructions(request)
        return {
            "summary": "Converted the request into a simple step-by-step checklist.",
            "data": {"steps": steps},
            "tool_calls": ["simplify_instructions"],
        }
    raise ValueError(f"Unknown specialist agent: {agent_id}")
