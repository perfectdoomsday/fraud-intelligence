# Machine-learning pipeline

## Runtime inference

The runtime inference interface is `FraudInference.predict(features) -> (fraud_probability, anomaly_score, model_version)`.

- If `MODEL_ARTIFACT_PATH` points to a serialized model bundle, the system loads `supervised_model`, optional `anomaly_model`, `anomaly_bounds`, `feature_columns`, and `version`.
- The bootstrap demo artifact is a RandomForest classifier and IsolationForest trained from synthetic feature rows.
- If the artifact is absent/unreadable, a deterministic transparent heuristic produces a fallback probability and anomaly signal. It is named `rules-fallback-v1`; it is not a learned model.
- Anomaly decision-function values are normalized into a 0–1 scale using training bounds before ensemble use. They are not treated as raw probabilities.

## Offline training

`ml/training/train.py` loads labelled historical CSV, sorts by transaction timestamp, and creates chronological training, validation, and test windows. XGBoost and LightGBM candidates are trained and compared using validation PR-AUC. The winning algorithm is refit on train+validation and paired with IsolationForest trained on the non-fraud portion. The temporal test scores are written to a report and are not used to select the candidate.

The script is an experiment baseline, not a complete institution-grade training framework. Add hyperparameter search, probability calibration, operating-threshold tuning, population/segment evaluation, financial loss analysis, model card, MLflow run/registry integration and artifact signature checks before release.

## Explainability

The inference path attempts TreeExplainer for compatible serialized tree models. If SHAP cannot explain the active model, the API returns `source=RISK_SIGNALS_NOT_SHAP` and transparent named risk signals. The UI/API must not label these heuristic signals as SHAP attributions. Global feature importance can be derived from the registered model artifact in a later model-intelligence view.

## Evaluation protocol

Prioritize precision, recall, F1, PR-AUC, ROC-AUC, false-positive rate, false-negative rate, and business impact. A random train/test split leaks temporal information for evolving fraud; use future-period holdouts and consider a rolling backtest. Accuracy alone is misleading under severe class imbalance.

Synthetic labels and generated patterns allow pipeline tests only. They do not represent adversarial fraud behaviour, real customer distributions, real merchant dynamics, model drift, or real-world investigator capacity.
