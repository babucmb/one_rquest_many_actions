from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class WorkflowRequest(BaseModel):
    request: str = Field(min_length=3, max_length=4000)

    @field_validator("request")
    @classmethod
    def request_must_have_text(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise ValueError("request must contain at least three non-space characters")
        return value


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    due_date: str | None = Field(default=None, max_length=40)
    priority: Literal["low", "normal", "high"] = "normal"

    @field_validator("title")
    @classmethod
    def title_must_have_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("title must not be blank")
        return value

    @field_validator("due_date")
    @classmethod
    def due_date_must_be_iso_date(cls, value: str | None) -> str | None:
        if value is not None:
            try:
                return date.fromisoformat(value).isoformat()
            except ValueError as error:
                raise ValueError("due_date must use YYYY-MM-DD format") from error
        return value


class TaskUpdate(BaseModel):
    status: Literal["pending", "in_progress", "done"]


class ReplyDraftRequest(BaseModel):
    reply_text: str = Field(min_length=1, max_length=4000)

    @field_validator("reply_text")
    @classmethod
    def reply_must_have_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("reply_text must not be blank")
        return value


class MealPlanRequest(BaseModel):
    budget: float | None = Field(default=None, ge=0)


class MealPlanSaveRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    budget: float | None = Field(default=None, ge=0)

    @field_validator("name")
    @classmethod
    def name_must_have_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("name must not be blank")
        return value


class AppointmentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    starts_at: str = Field(min_length=1, max_length=40)
    owner: str = Field(default="You", max_length=120)

    @field_validator("title")
    @classmethod
    def appointment_title_must_have_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("title must not be blank")
        return value

    @field_validator("starts_at")
    @classmethod
    def appointment_time_must_be_iso(cls, value: str) -> str:
        try:
            return datetime.fromisoformat(value).isoformat()
        except ValueError as error:
            raise ValueError("starts_at must be an ISO-8601 date-time") from error


class ReminderCreate(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    remind_at: str = Field(min_length=1, max_length=40)
    owner: str = Field(default="You", max_length=120)

    @field_validator("title")
    @classmethod
    def reminder_title_must_have_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("title must not be blank")
        return value

    @field_validator("remind_at")
    @classmethod
    def reminder_time_must_be_iso(cls, value: str) -> str:
        try:
            return datetime.fromisoformat(value).isoformat()
        except ValueError as error:
            raise ValueError("remind_at must be an ISO-8601 date-time") from error


class CustomerFollowupRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)

    @field_validator("message")
    @classmethod
    def customer_message_must_have_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("message must not be blank")
        return value


class ChecklistRequest(BaseModel):
    task_ids: list[str] = Field(max_length=50)


class TripUpdateApprovalRequest(BaseModel):
    destination: str | None = Field(default=None, min_length=1, max_length=160)
    starts_on: str | None = Field(default=None, min_length=10, max_length=40)
    ends_on: str | None = Field(default=None, min_length=10, max_length=40)
    estimated_cost: float | None = Field(default=None, ge=0)

    @field_validator("destination")
    @classmethod
    def destination_must_have_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("destination must not be blank")
        return value

    @field_validator("starts_on", "ends_on")
    @classmethod
    def trip_dates_must_be_iso(cls, value: str | None) -> str | None:
        if value is None:
            return value
        try:
            return date.fromisoformat(value).isoformat()
        except ValueError as error:
            raise ValueError("trip dates must use YYYY-MM-DD format") from error

    @model_validator(mode="after")
    def must_include_a_change(self) -> "TripUpdateApprovalRequest":
        if all(
            value is None
            for value in (
                self.destination,
                self.starts_on,
                self.ends_on,
                self.estimated_cost,
            )
        ):
            raise ValueError("at least one trip field must be supplied")
        return self


class ApprovalDecision(BaseModel):
    approved: bool


class FamilyCheckinDraftRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)

    @field_validator("message")
    @classmethod
    def message_must_have_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("message must not be blank")
        return value


class AgentRunResponse(BaseModel):
    agent: str
    summary: str
    data: dict[str, Any]
    tool_calls: list[str]


class TaskResponse(BaseModel):
    id: str
    title: str
    due_date: str | None
    priority: str
    status: str
    source: str


class TaskPageResponse(BaseModel):
    items: list[TaskResponse]
    total: int
    offset: int
    limit: int


class AgentInfo(BaseModel):
    id: str
    name: str
    description: str
    capability: str


class EventResponse(BaseModel):
    id: str
    agent: str
    event_type: str
    message: str
    details: dict[str, Any] | None = None
    created_at: datetime


class WorkflowResponse(BaseModel):
    id: str
    request: str
    mode: str
    status: str
    response: str | None
    created_at: datetime
    agents: list[dict[str, Any]] = Field(default_factory=list)
    events: list[EventResponse] = Field(default_factory=list)


class RuntimeInfo(BaseModel):
    mode: str
    model: str
