from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def new_id() -> str:
    return str(uuid4())


def utc_now() -> datetime:
    return datetime.now(UTC)


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    due_date: Mapped[str | None] = mapped_column(String(40))
    priority: Mapped[str] = mapped_column(String(16), default="normal")
    status: Mapped[str] = mapped_column(String(20), default="pending")
    source: Mapped[str] = mapped_column(String(32), default="demo")


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    description: Mapped[str] = mapped_column(String(240), nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    recorded_on: Mapped[str] = mapped_column(String(40), nullable=False)


class Bill(Base):
    __tablename__ = "bills"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    due_date: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="upcoming")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    sender: Mapped[str] = mapped_column(String(160), nullable=False)
    subject: Mapped[str] = mapped_column(String(240), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    received_at: Mapped[str] = mapped_column(String(40), nullable=False)
    reply_draft: Mapped[str | None] = mapped_column(Text)


class Trip(Base):
    __tablename__ = "trips"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    destination: Mapped[str] = mapped_column(String(160), nullable=False)
    starts_on: Mapped[str] = mapped_column(String(40), nullable=False)
    ends_on: Mapped[str] = mapped_column(String(40), nullable=False)
    estimated_cost: Mapped[float] = mapped_column(Float, nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="")


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workflow_id: Mapped[str | None] = mapped_column(ForeignKey("workflows.id"))
    action: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    approved: Mapped[bool | None] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class MealPlanRecord(Base):
    __tablename__ = "meal_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    plan: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    estimated_total: Mapped[float] = mapped_column(Float, nullable=False)
    data_source: Mapped[str] = mapped_column(String(60), default="sample_pantry_and_estimates")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ShoppingListItem(Base):
    __tablename__ = "shopping_list_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    list_id: Mapped[str] = mapped_column(
        ForeignKey("meal_plans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ingredient: Mapped[str] = mapped_column(String(160), nullable=False)
    quantity: Mapped[str] = mapped_column(String(80), default="1")
    estimated_cost: Mapped[float | None] = mapped_column(Float)
    checked: Mapped[bool] = mapped_column(Boolean, default=False)


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    starts_at: Mapped[str] = mapped_column(String(40), nullable=False)
    owner: Mapped[str] = mapped_column(String(120), nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="")


class FamilyCheckinDraft(Base):
    __tablename__ = "family_checkin_drafts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    appointment_id: Mapped[str] = mapped_column(ForeignKey("appointments.id"), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    remind_at: Mapped[str] = mapped_column(String(40), nullable=False)
    owner: Mapped[str] = mapped_column(String(120), default="You")
    source: Mapped[str] = mapped_column(String(32), default="local_demo")


class InventoryItem(Base):
    __tablename__ = "inventory"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    reorder_at: Mapped[int] = mapped_column(Integer, nullable=False)
    unit: Mapped[str] = mapped_column(String(32), default="units")


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    customer: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    due_date: Mapped[str] = mapped_column(String(40), nullable=False)


class CustomerFollowupDraft(Base):
    __tablename__ = "customer_followup_drafts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), nullable=False)
    customer: Mapped[str] = mapped_column(String(160), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class UserPreference(Base):
    __tablename__ = "user_preferences"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[Any] = mapped_column(JSON, nullable=False)


class Workflow(Base):
    __tablename__ = "workflows"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    request: Mapped[str] = mapped_column(Text, nullable=False)
    mode: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="running")
    response: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    events: Mapped[list["WorkflowEvent"]] = relationship(
        back_populates="workflow", cascade="all, delete-orphan", order_by="WorkflowEvent.created_at"
    )


class WorkflowEvent(Base):
    __tablename__ = "workflow_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workflow_id: Mapped[str] = mapped_column(ForeignKey("workflows.id"), nullable=False)
    agent: Mapped[str] = mapped_column(String(80), nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    workflow: Mapped[Workflow] = relationship(back_populates="events")
