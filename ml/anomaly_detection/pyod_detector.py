"""Optional PyOD adapter for comparing unsupervised anomaly algorithms."""
from __future__ import annotations

import numpy as np


class PyODDetector:
    def __init__(self, contamination: float = 0.02, method: str = "iforest"):
        self.contamination = contamination
        self.method = method
        self.model = None

    def fit(self, x):
        if self.method == "iforest":
            from pyod.models.iforest import IForest
            self.model = IForest(contamination=self.contamination, random_state=42)
        elif self.method == "lof":
            from pyod.models.lof import LOF
            self.model = LOF(contamination=self.contamination)
        else:
            raise ValueError("method must be 'iforest' or 'lof'")
        self.model.fit(np.asarray(x))
        return self

    def anomaly_scores(self, x) -> np.ndarray:
        if self.model is None:
            raise RuntimeError("Call fit() before anomaly_scores()")
        scores = np.asarray(self.model.decision_function(np.asarray(x)), dtype=float)
        low, high = float(scores.min()), float(scores.max())
        return np.zeros_like(scores) if high == low else (scores - low) / (high - low)
