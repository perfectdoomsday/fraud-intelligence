import logging
from pathlib import Path

import joblib
import numpy as np

from app.core.config import settings
from app.services.feature_engineering import FEATURE_COLUMNS

logger = logging.getLogger(__name__)


class FraudInference:
    def __init__(self):
        self.bundle = None
        self.model_version = "rules-fallback-v1"
        path = Path(settings.model_artifact_path)
        if path.exists():
            try:
                self.bundle = joblib.load(path)
                self.model_version = str(self.bundle.get("version", "local-model"))
                logger.info("Loaded fraud model artifact %s", path)
            except Exception:
                logger.exception("Could not load model artifact; using transparent rule baseline")

    def predict(self, features: dict[str, float]) -> tuple[float, float, str]:
        vector = np.asarray([[features.get(name, 0.0) for name in FEATURE_COLUMNS]], dtype=float)
        if self.bundle and self.bundle.get("supervised_model"):
            model = self.bundle["supervised_model"]
            probability = float(model.predict_proba(vector)[0, 1])
            anomaly_model = self.bundle.get("anomaly_model")
            if anomaly_model is not None:
                raw = float(anomaly_model.decision_function(vector)[0])
                low, high = self.bundle.get("anomaly_bounds", [-1.0, 1.0])
                anomaly = float(np.clip((high - raw) / max(high - low, 1e-9), 0, 1))
            else:
                anomaly = self._heuristic_anomaly(features)
            return probability, anomaly, self.model_version
        # Explicit, deterministic fallback; never presented as a trained ML model.
        anomaly = self._heuristic_anomaly(features)
        logit = (
            -4.0 + 0.85 * min(features.get("amount_to_customer_avg", 1), 8)
            + 0.32 * features.get("transactions_5m", 0)
            + 0.12 * features.get("transactions_1h", 0)
            + 1.1 * features.get("new_device", 0)
            + 0.9 * features.get("new_location", 0)
            + 1.1 * features.get("geo_inconsistency", 0)
            + 0.8 * features.get("is_card_not_present", 0)
        )
        probability = float(1 / (1 + np.exp(-np.clip(logit, -20, 20))))
        return probability, anomaly, self.model_version

    @staticmethod
    def _heuristic_anomaly(features: dict[str, float]) -> float:
        score = (
            0.26 * min(features.get("amount_to_customer_avg", 1) / 5, 1)
            + 0.18 * min(features.get("transactions_5m", 0) / 5, 1)
            + 0.12 * min(features.get("transactions_1h", 0) / 12, 1)
            + 0.16 * features.get("new_device", 0)
            + 0.12 * features.get("new_location", 0)
            + 0.10 * features.get("geo_inconsistency", 0)
            + 0.06 * min(features.get("merchant_risk_rate", 0) / 0.2, 1)
        )
        return float(np.clip(score, 0, 1))
