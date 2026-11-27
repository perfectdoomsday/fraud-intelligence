import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.models import (
    Account, Customer, Device, FraudAlert, FraudPrediction, Merchant, NotificationEvent,
    RiskScore, Transaction, TransactionFeature,
)
from app.services.decision_engine import decide
from app.services.explainability import build_explanation
from app.services.feature_engineering import build_features
from app.services.inference import FraudInference
from app.services.risk_engine import calculate_risk_score, risk_category
from app.services.state_store import TransactionStateStore
from app.services.notification_service import send_alert_notification
from app.core.metrics import ALERTS_CREATED, TRANSACTIONS_PROCESSED

logger = logging.getLogger(__name__)
state_store = TransactionStateStore()
inference = FraudInference()


def process_transaction(db: Session, payload: dict) -> dict:
    existing = db.query(Transaction).filter(Transaction.transaction_id == payload["transaction_id"]).first()
    if existing and existing.processing_status == "PROCESSED":
        return {"status": "duplicate", "transaction_id": existing.transaction_id}

    timestamp = payload.get("timestamp") or datetime.now(timezone.utc)
    if isinstance(timestamp, str):
        timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    payload["timestamp"] = timestamp
    tx_state = state_store.update_and_get({**payload, "timestamp": timestamp})
    features = build_features({**payload, "timestamp": timestamp}, tx_state)
    probability, anomaly, model_version = inference.predict(features)
    score = calculate_risk_score(probability, anomaly, features)
    category = risk_category(score)
    decision, rules = decide(score)
    explanation = build_explanation(features, probability, score, inference.bundle)

    # Dimension upserts preserve referential integrity for normalized customer/account/device data.
    customer = db.get(Customer, payload["customer_id"])
    if customer is None:
        db.add(Customer(customer_id=payload["customer_id"]))
        db.flush()
    account = db.get(Account, payload["account_id"])
    if account is None:
        db.add(Account(account_id=payload["account_id"], customer_id=payload["customer_id"]))
    elif account.customer_id != payload["customer_id"]:
        raise ValueError("account_id is already associated with a different customer_id")
    db.flush()
    merchant = db.get(Merchant, payload["merchant_id"])
    if merchant is None:
        db.add(Merchant(merchant_id=payload["merchant_id"], category=payload.get("merchant_category", "other")))
    device = db.get(Device, payload["device_id"])
    if device is None:
        db.add(Device(device_id=payload["device_id"], last_seen_at=timestamp))
    else:
        device.last_seen_at = timestamp
    db.flush()

    if existing is None:
        existing = Transaction(
            **{key: payload.get(key) for key in [
                "transaction_id", "customer_id", "account_id", "amount", "currency", "merchant_id",
                "merchant_category", "timestamp", "payment_method", "device_id", "ip_address", "latitude",
                "longitude", "channel", "transaction_status", "label_is_fraud",
            ]}
        )
        db.add(existing)
    db.flush()
    existing.processing_status = "PROCESSED"
    existing.fraud_probability = probability
    existing.anomaly_score = anomaly
    existing.risk_score = score
    existing.risk_category = category
    existing.decision = decision
    existing.model_version = model_version
    existing.features = features
    existing.explanation = explanation

    prediction = FraudPrediction(
        transaction_id=existing.transaction_id, fraud_probability=probability, anomaly_score=anomaly,
        risk_score=score, risk_category=category, decision=decision,
        model_version=model_version, explanation=explanation,
    )
    db.add(prediction)
    db.add(TransactionFeature(transaction_id=existing.transaction_id, features=features))
    db.add(RiskScore(transaction_id=existing.transaction_id, score=score, category=category,
                     factors={"fraud_probability": probability, "anomaly_score": anomaly}))
    created_alert = None
    if category in {"HIGH", "CRITICAL"}:
        severity = category
        created_alert = FraudAlert(
            alert_id=f"ALT-{uuid.uuid4().hex[:12].upper()}",
            transaction_id=existing.transaction_id,
            customer_id=existing.customer_id,
            severity=severity,
            risk_score=score,
            triggered_rules=rules + (["ANOMALY_SCORE_ELEVATED"] if anomaly >= 0.65 else []),
            explanation=explanation,
        )
        db.add(created_alert)
        db.add(NotificationEvent(event_id=f"NOTIF-{uuid.uuid4().hex[:12].upper()}",
                                 event_type="FRAUD_ALERT", channel="local-log", status="RECORDED",
                                 payload={"alert_id": created_alert.alert_id, "severity": category,
                                          "transaction_id": existing.transaction_id}))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        committed = db.query(Transaction).filter(Transaction.transaction_id == payload["transaction_id"]).first()
        if committed and committed.processing_status == "PROCESSED":
            logger.info("Duplicate event ignored: %s", payload["transaction_id"])
            return {"status": "duplicate", "transaction_id": payload["transaction_id"]}
        # A concurrent dimension upsert may have won the unique-key race; retry the event
        # so the next attempt can read that committed dimension row instead of losing it.
        raise
    db.refresh(existing)
    TRANSACTIONS_PROCESSED.inc()
    if created_alert is not None:
        ALERTS_CREATED.labels(category).inc()
        send_alert_notification(created_alert.alert_id, category, existing.transaction_id)
    return {
        "status": "processed", "transaction_id": existing.transaction_id,
        "fraud_probability": probability, "anomaly_score": anomaly, "risk_score": score,
        "risk_category": category, "decision": decision, "model_version": model_version,
        "alert_created": category in {"HIGH", "CRITICAL"},
    }
