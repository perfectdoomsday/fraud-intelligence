"""Event contract helpers shared by ingestion tests and integration adapters."""
from datetime import datetime
from pydantic import ValidationError
from app.schemas.transactions import TransactionCreate


def validate_event(payload: dict) -> dict:
    """Validate and normalize the public transaction event contract."""
    try:
        event = TransactionCreate.model_validate(payload)
    except ValidationError:
        raise
    return event.model_dump(mode="json")


def event_time(payload: dict) -> datetime:
    value = payload["timestamp"]
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
