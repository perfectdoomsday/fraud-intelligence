"""Small reference-vs-current drift report builder. Evidently integration is optional."""
from __future__ import annotations

import uuid
import numpy as np
import pandas as pd


def compare_feature_frames(reference: pd.DataFrame, current: pd.DataFrame, threshold: float = 0.20) -> dict:
    affected, details = [], {}
    for column in reference.select_dtypes(include=["number"]).columns.intersection(current.columns):
        base = reference[column].dropna().to_numpy(dtype=float)
        live = current[column].dropna().to_numpy(dtype=float)
        if len(base) < 20 or len(live) < 20:
            continue
        bins = np.histogram_bin_edges(base, bins=10)
        if len(bins) < 2 or bins[0] == bins[-1]:
            continue
        p = np.histogram(base, bins=bins)[0].astype(float) + 1
        q = np.histogram(live, bins=bins)[0].astype(float) + 1
        p, q = p / p.sum(), q / q.sum()
        psi = float(np.sum((q - p) * np.log(q / p)))
        details[column] = {"population_stability_index": round(psi, 6)}
        if psi >= threshold:
            affected.append(column)
    return {"report_id": f"DRIFT-{uuid.uuid4().hex[:12].upper()}",
            "drift_detected": bool(affected), "drift_share": len(affected) / max(len(details), 1),
            "affected_features": affected, "details": details,
            "note": "PSI is a screening statistic; investigate data quality and label/segment effects before retraining."}
