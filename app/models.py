from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class Category(str, Enum):
    billing = "billing"
    bug = "bug"
    account = "account"
    feature_request = "feature_request"
    other = "other"


class Priority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"


class Status(str, Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"


class TicketCreate(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    body: str = Field(min_length=3, max_length=5000)


class StatusUpdate(BaseModel):
    status: Status


class Classification(BaseModel):
    category: Category
    priority: Priority


class Ticket(BaseModel):
    id: int
    title: str
    body: str
    category: Category
    priority: Priority
    status: Status
    created_at: datetime
