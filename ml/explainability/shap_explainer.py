"""On-demand SHAP explanation helper for tree-based estimators."""
import numpy as np


def explain_tree_model(model, feature_names: list[str], feature_vector: list[float], top_k: int = 8):
    import shap
    row = np.asarray([feature_vector], dtype=float)
    explanation = shap.TreeExplainer(model)(row)
    values = explanation.values
    if values.ndim == 3:
        values = values[0, :, 1]
    else:
        values = values[0]
    ranked = sorted(zip(feature_names, values.tolist()), key=lambda pair: abs(pair[1]), reverse=True)[:top_k]
    return [{"feature": name, "shap_value": float(value)} for name, value in ranked]
