from app.services.feature_engineering import FEATURE_COLUMNS

FEATURE_LABELS = {
    "amount_to_customer_avg": "Amount relative to customer baseline",
    "transactions_5m": "Transactions in the last 5 minutes",
    "transactions_1h": "Transactions in the last hour",
    "new_device": "Device not previously associated with customer",
    "new_location": "New transaction location",
    "geo_inconsistency": "Geographic movement inconsistent with elapsed time",
    "distance_from_previous_km": "Distance from previous transaction",
    "merchant_risk_rate": "Historical merchant risk rate",
    "is_card_not_present": "Card-not-present channel",
}


def build_explanation(features: dict, probability: float, risk_score: int, model_bundle=None) -> dict:
    """Return SHAP values when supported; otherwise label signals as heuristics, not SHAP."""
    if model_bundle and model_bundle.get("supervised_model"):
        try:
            import shap
            import numpy as np
            model = model_bundle["supervised_model"]
            values = shap.TreeExplainer(model)(np.asarray([[features.get(k, 0) for k in FEATURE_COLUMNS]]))
            raw = values.values
            if raw.ndim == 3:
                raw = raw[0, :, 1]
            else:
                raw = raw[0]
            ranked = sorted(zip(FEATURE_COLUMNS, raw.tolist()), key=lambda item: abs(item[1]), reverse=True)[:6]
            return {
                "source": "SHAP",
                "model_probability": round(probability, 6),
                "risk_score": risk_score,
                "top_contributors": [
                    {"feature": FEATURE_LABELS.get(k, k), "feature_key": k, "value": features.get(k),
                     "contribution": round(float(v), 6), "direction": "increases_risk" if v > 0 else "decreases_risk"}
                    for k, v in ranked
                ],
            }
        except Exception:
            pass
    # Human-readable risk signals with transparent weights; these are not SHAP values.
    signal_weights = {
        "amount_to_customer_avg": max(0, min(features.get("amount_to_customer_avg", 1) - 1, 8)) / 8,
        "transactions_5m": min(features.get("transactions_5m", 0) / 5, 1),
        "transactions_1h": min(features.get("transactions_1h", 0) / 12, 1),
        "new_device": features.get("new_device", 0),
        "new_location": features.get("new_location", 0),
        "geo_inconsistency": features.get("geo_inconsistency", 0),
        "merchant_risk_rate": min(features.get("merchant_risk_rate", 0) / 0.2, 1),
    }
    ranked = sorted(signal_weights.items(), key=lambda item: item[1], reverse=True)[:6]
    return {
        "source": "RISK_SIGNALS_NOT_SHAP",
        "model_probability": round(probability, 6),
        "risk_score": risk_score,
        "top_contributors": [
            {"feature": FEATURE_LABELS.get(k, k), "feature_key": k, "value": features.get(k),
             "contribution": round(float(v), 4), "direction": "increases_risk"}
            for k, v in ranked if v > 0
        ],
        "note": "Install/use a compatible tree model and SHAP to obtain model-attribution values. These signals are transparent rules, not SHAP values.",
    }
