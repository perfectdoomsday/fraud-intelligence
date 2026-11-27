import math
from datetime import datetime, timezone
from typing import Any

import numpy as np

FEATURE_COLUMNS = [
    "amount", "log_amount", "transaction_hour", "day_of_week", "is_weekend",
    "transactions_5m", "transactions_1h", "spend_1h", "customer_avg_amount_7d",
    "amount_to_customer_avg", "minutes_since_last_txn", "new_device", "new_location",
    "distance_from_previous_km", "geo_inconsistency", "is_card_not_present", "merchant_risk_rate",
]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    delta_p = math.radians(lat2 - lat1)
    delta_l = math.radians(lon2 - lon1)
    a = math.sin(delta_p / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(delta_l / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def build_features(transaction: dict[str, Any], state: dict[str, Any] | None = None) -> dict[str, float]:
    state = state or {}
    timestamp = transaction.get("timestamp") or datetime.now(timezone.utc)
    if isinstance(timestamp, str):
        timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    amount = float(transaction["amount"])
    avg = max(float(state.get("customer_avg_amount_7d", 0) or 0), 1.0)
    lat, lon = transaction.get("latitude"), transaction.get("longitude")
    previous = state.get("previous_location") or {}
    distance = 0.0
    if lat is not None and lon is not None and previous.get("latitude") is not None:
        distance = haversine_km(float(lat), float(lon), float(previous["latitude"]), float(previous["longitude"]))
    elapsed = float(state.get("minutes_since_last_txn", 1440) or 1440)
    features = {
        "amount": amount,
        "log_amount": float(np.log1p(amount)),
        "transaction_hour": float(timestamp.hour),
        "day_of_week": float(timestamp.weekday()),
        "is_weekend": float(timestamp.weekday() >= 5),
        "transactions_5m": float(state.get("transactions_5m", 0)),
        "transactions_1h": float(state.get("transactions_1h", 0)),
        "spend_1h": float(state.get("spend_1h", 0)),
        "customer_avg_amount_7d": avg,
        "amount_to_customer_avg": amount / avg,
        "minutes_since_last_txn": min(elapsed, 10080.0),
        "new_device": float(state.get("new_device", 1)),
        "new_location": float(state.get("new_location", 1)),
        "distance_from_previous_km": distance,
        "geo_inconsistency": float(distance > max(elapsed, 1) * 1.5),
        "is_card_not_present": float(transaction.get("channel", "online") in {"online", "ecommerce", "mobile"}),
        "merchant_risk_rate": float(state.get("merchant_risk_rate", 0.02)),
    }
    return {key: float(value) for key, value in features.items()}
