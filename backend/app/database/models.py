from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Role(Base):
    __tablename__ = "roles"
    name: Mapped[str] = mapped_column(String(40), primary_key=True)
    description: Mapped[str] = mapped_column(String(255), default="")


class Permission(Base):
    __tablename__ = "permissions"
    name: Mapped[str] = mapped_column(String(60), primary_key=True)
    description: Mapped[str] = mapped_column(String(255), default="")


class RolePermission(Base):
    __tablename__ = "role_permissions"
    role_name: Mapped[str] = mapped_column(ForeignKey("roles.name", ondelete="CASCADE"), primary_key=True)
    permission_name: Mapped[str] = mapped_column(ForeignKey("permissions.name", ondelete="CASCADE"), primary_key=True)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(ForeignKey("roles.name"), default="read_only_auditor")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Customer(Base):
    __tablename__ = "customers"
    customer_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    risk_segment: Mapped[str] = mapped_column(String(30), default="UNCLASSIFIED")


class Account(Base):
    __tablename__ = "accounts"
    account_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.customer_id"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Merchant(Base):
    __tablename__ = "merchants"
    merchant_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    category: Mapped[str] = mapped_column(String(80), default="other")
    risk_rate: Mapped[float] = mapped_column(Float, default=0.02)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Device(Base):
    __tablename__ = "devices"
    device_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    reputation_score: Mapped[float] = mapped_column(Float, default=0.0)


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (Index("ix_transactions_created_risk", "created_at", "risk_score"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    transaction_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.customer_id"), index=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.account_id"), index=True)
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    merchant_id: Mapped[str] = mapped_column(ForeignKey("merchants.merchant_id"), index=True)
    merchant_category: Mapped[str] = mapped_column(String(80), default="other")
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    payment_method: Mapped[str] = mapped_column(String(40), default="card")
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.device_id"), index=True)
    ip_address: Mapped[str] = mapped_column(String(64), default="0.0.0.0")
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    channel: Mapped[str] = mapped_column(String(40), default="online")
    transaction_status: Mapped[str] = mapped_column(String(40), default="completed")
    label_is_fraud: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    processing_status: Mapped[str] = mapped_column(String(24), default="RECEIVED", index=True)
    fraud_probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    anomaly_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    risk_category: Mapped[str | None] = mapped_column(String(20), nullable=True)
    decision: Mapped[str | None] = mapped_column(String(40), nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    features: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    explanation: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    event_created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class TransactionFeature(Base):
    __tablename__ = "transaction_features"
    transaction_id: Mapped[str] = mapped_column(ForeignKey("transactions.transaction_id", ondelete="CASCADE"), primary_key=True)
    features: Mapped[dict[str, Any]] = mapped_column(JSON)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class FraudPrediction(Base):
    __tablename__ = "fraud_predictions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    transaction_id: Mapped[str] = mapped_column(ForeignKey("transactions.transaction_id", ondelete="CASCADE"), index=True)
    fraud_probability: Mapped[float] = mapped_column(Float)
    anomaly_score: Mapped[float] = mapped_column(Float)
    risk_score: Mapped[int] = mapped_column(Integer)
    risk_category: Mapped[str] = mapped_column(String(20))
    decision: Mapped[str] = mapped_column(String(40))
    model_version: Mapped[str] = mapped_column(String(100))
    explanation: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RiskScore(Base):
    __tablename__ = "risk_scores"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    transaction_id: Mapped[str] = mapped_column(ForeignKey("transactions.transaction_id", ondelete="CASCADE"), index=True)
    score: Mapped[int] = mapped_column(Integer)
    category: Mapped[str] = mapped_column(String(20))
    factors: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class FraudAlert(Base):
    __tablename__ = "fraud_alerts"
    __table_args__ = (UniqueConstraint("transaction_id", "alert_type", name="uq_alert_transaction_type"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    alert_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    transaction_id: Mapped[str] = mapped_column(ForeignKey("transactions.transaction_id", ondelete="CASCADE"), index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.customer_id"), index=True)
    alert_type: Mapped[str] = mapped_column(String(50), default="HIGH_RISK")
    severity: Mapped[str] = mapped_column(String(20), index=True)
    risk_score: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(30), default="NEW", index=True)
    triggered_rules: Mapped[list[str]] = mapped_column(JSON, default=list)
    explanation: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    assigned_to: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class InvestigationCase(Base):
    __tablename__ = "investigation_cases"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    alert_id: Mapped[str] = mapped_column(ForeignKey("fraud_alerts.alert_id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(30), default="OPEN", index=True)
    disposition: Mapped[str | None] = mapped_column(String(40), nullable=True)
    assigned_to: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    notes: Mapped[list["InvestigationNote"]] = relationship(back_populates="case", cascade="all, delete-orphan")


class InvestigationNote(Base):
    __tablename__ = "investigation_notes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("investigation_cases.id", ondelete="CASCADE"), index=True)
    author: Mapped[str] = mapped_column(String(255))
    note: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    case: Mapped[InvestigationCase] = relationship(back_populates="notes")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor: Mapped[str] = mapped_column(String(255), index=True)
    action: Mapped[str] = mapped_column(String(100), index=True)
    resource_type: Mapped[str] = mapped_column(String(80))
    resource_id: Mapped[str] = mapped_column(String(100))
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ModelVersion(Base):
    __tablename__ = "model_versions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    artifact_uri: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(30), default="CANDIDATE")
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ModelMetric(Base):
    __tablename__ = "model_metrics"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_version: Mapped[str] = mapped_column(ForeignKey("model_versions.version", ondelete="CASCADE"), index=True)
    metric_name: Mapped[str] = mapped_column(String(80))
    metric_value: Mapped[float] = mapped_column(Float)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DriftReport(Base):
    __tablename__ = "drift_reports"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    report_id: Mapped[str] = mapped_column(String(80), unique=True)
    drift_detected: Mapped[bool] = mapped_column(Boolean, default=False)
    drift_share: Mapped[float] = mapped_column(Float, default=0.0)
    affected_features: Mapped[list[str]] = mapped_column(JSON, default=list)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RetrainingJob(Base):
    __tablename__ = "retraining_jobs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    trigger_reason: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(30), default="QUEUED")
    candidate_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class NotificationEvent(Base):
    __tablename__ = "notification_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    event_type: Mapped[str] = mapped_column(String(80))
    channel: Mapped[str] = mapped_column(String(40), default="local-log")
    status: Mapped[str] = mapped_column(String(30), default="RECORDED")
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
