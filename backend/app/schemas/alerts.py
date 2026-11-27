from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    alert_id: str
    transaction_id: str
    customer_id: str
    severity: str
    risk_score: int
    status: str
    triggered_rules: list[str]
    explanation: dict
    assigned_to: str | None
    created_at: datetime


class AlertStatusUpdate(BaseModel):
    status: str = Field(pattern="^(ACKNOWLEDGED|INVESTIGATING|CONFIRMED_FRAUD|FALSE_POSITIVE|CLOSED)$")


class AssignAlert(BaseModel):
    assigned_to: str = Field(min_length=3, max_length=255)
