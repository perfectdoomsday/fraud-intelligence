"""Evaluation helpers; use chronological holdout data, never a random split for production claims."""
from sklearn.metrics import average_precision_score, precision_recall_curve


def find_threshold_for_precision(y_true, probabilities, minimum_precision: float = 0.90) -> dict:
    precision, recall, thresholds = precision_recall_curve(y_true, probabilities)
    valid = [(float(p), float(r), float(t)) for p, r, t in zip(precision[:-1], recall[:-1], thresholds) if p >= minimum_precision]
    if not valid:
        return {"threshold": 1.0, "precision": 0.0, "recall": 0.0, "pr_auc": float(average_precision_score(y_true, probabilities))}
    best = max(valid, key=lambda row: row[1])
    return {"threshold": best[2], "precision": best[0], "recall": best[1],
            "pr_auc": float(average_precision_score(y_true, probabilities))}
