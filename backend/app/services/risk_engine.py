from app.core.config import settings


def calculate_risk_score(probability: float, anomaly_score: float, features: dict) -> int:
    total_weight = settings.supervised_weight + settings.anomaly_weight
    if total_weight <= 0:
        hybrid = probability
    else:
        hybrid = (settings.supervised_weight * probability + settings.anomaly_weight * anomaly_score) / total_weight
    behavioural = min(
        1.0,
        0.18 * min(features.get("transactions_5m", 0) / 5, 1)
        + 0.16 * min(features.get("amount_to_customer_avg", 1) / 6, 1)
        + 0.12 * features.get("new_device", 0)
        + 0.10 * features.get("new_location", 0)
        + 0.08 * features.get("geo_inconsistency", 0),
    )
    return int(round(max(0, min(100, 100 * (0.82 * hybrid + 0.18 * behavioural)))))


def risk_category(score: int) -> str:
    if score >= settings.risk_critical_threshold:
        return "CRITICAL"
    if score >= settings.risk_high_threshold:
        return "HIGH"
    if score >= settings.risk_medium_threshold:
        return "MEDIUM"
    return "LOW"
