import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.decision_engine import decide
from app.services.feature_engineering import build_features, haversine_km
from app.services.risk_engine import calculate_risk_score, risk_category


def test_risk_score_is_bounded():
    score = calculate_risk_score(0.98, 0.99, {"transactions_5m": 5, "amount_to_customer_avg": 10,
                                             "new_device": 1, "new_location": 1, "geo_inconsistency": 1})
    assert 0 <= score <= 100


def test_risk_categories_and_decisions():
    assert risk_category(10) == "LOW"
    assert risk_category(45) == "MEDIUM"
    assert risk_category(65) == "HIGH"
    assert risk_category(90) == "CRITICAL"
    assert decide(91)[0] == "ESCALATE"


def test_feature_builder_returns_required_columns():
    payload = {"amount": 1500, "timestamp": "2026-01-01T12:30:00+00:00", "channel": "online",
               "latitude": 28.6, "longitude": 77.2}
    features = build_features(payload, {"customer_avg_amount_7d": 1000, "transactions_5m": 2})
    assert features["amount_to_customer_avg"] == 1.5
    assert features["transactions_5m"] == 2
    assert len(features) >= 15


def test_haversine_distance_is_reasonable():
    assert 800 < haversine_km(28.6139, 77.2090, 19.0760, 72.8777) < 1200


def test_velocity_state_uses_prior_customer_events_only():
    from datetime import datetime, timezone, timedelta
    from app.services.state_store import TransactionStateStore

    store = TransactionStateStore()
    base = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    first = {
        "transaction_id": "TXN-STATE-1", "customer_id": "CUS-STATE", "device_id": "DEV-STATE",
        "amount": 100.0, "timestamp": base, "latitude": 28.6, "longitude": 77.2,
    }
    second = {**first, "transaction_id": "TXN-STATE-2", "amount": 300.0,
              "timestamp": base + timedelta(minutes=2)}
    first_state = store.update_and_get(first)
    second_state = store.update_and_get(second)
    assert first_state["transactions_5m"] == 0
    assert first_state["new_device"] == 1
    assert second_state["transactions_5m"] == 1
    assert second_state["new_device"] == 0
    assert second_state["customer_avg_amount_7d"] == 100.0
