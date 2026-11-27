from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, Field, field_validator


class TransactionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    transaction_id: str = Field(min_length=3, max_length=80)
    customer_id: str = Field(min_length=1, max_length=80)
    account_id: str = Field(min_length=1, max_length=80)
    amount: float = Field(gt=0, le=100_000_000)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    merchant_id: str = Field(min_length=1, max_length=80)
    merchant_category: str = Field(default="other", max_length=80)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    payment_method: str = Field(default="card", max_length=40)
    device_id: str = Field(min_length=1, max_length=100)
    ip_address: str = Field(default="0.0.0.0", max_length=64)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    channel: str = Field(default="online", max_length=40)
    transaction_status: str = Field(default="completed", max_length=40)
    label_is_fraud: bool | None = None

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    transaction_id: str
    customer_id: str
    amount: float
    currency: str
    merchant_id: str
    merchant_category: str
    timestamp: datetime
    processing_status: str
    fraud_probability: float | None
    anomaly_score: float | None
    risk_score: int | None
    risk_category: str | None
    decision: str | None
    model_version: str | None
    features: dict | None = None
    explanation: dict | None = None


class BulkTransactions(BaseModel):
    transactions: list[TransactionCreate] = Field(min_length=1, max_length=5000)


class PaginatedTransactions(BaseModel):
    items: list[TransactionOut]
    total: int
    page: int
    page_size: int
