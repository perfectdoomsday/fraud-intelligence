from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class CaseCreate(BaseModel):
    alert_id: str
    title: str = Field(min_length=3, max_length=255)
    assigned_to: str | None = None


class NoteCreate(BaseModel):
    note: str = Field(min_length=2, max_length=5000)


class NoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    author: str
    note: str
    created_at: datetime


class CaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    case_id: str
    alert_id: str
    title: str
    status: str
    disposition: str | None
    assigned_to: str | None
    created_at: datetime
    notes: list[NoteOut] = []


class CaseUpdate(BaseModel):
    status: str | None = Field(default=None, pattern="^(OPEN|INVESTIGATING|CONFIRMED_FRAUD|FALSE_POSITIVE|CLOSED)$")
    disposition: str | None = Field(default=None, max_length=40)
    assigned_to: str | None = Field(default=None, max_length=255)
