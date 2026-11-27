# Database schema

SQLAlchemy models are in `backend/app/database/models.py`; Alembic baseline is in `backend/migrations/versions/0001_initial_schema.py`.

| Table | Purpose / key relationships |
|---|---|
| `roles`, `permissions`, `role_permissions` | Role catalogue and permission mapping |
| `users` | Argon2 hash, active state, role FK |
| `customers` | Customer master record |
| `accounts` | Account-to-customer relationship |
| `merchants` | Merchant category and risk-rate master data |
| `devices` | Device first/last-seen metadata |
| `transactions` | Transaction facts, event time, processing state, model result, score and explanation |
| `transaction_features` | Point-in-time feature snapshot per transaction |
| `fraud_predictions` | Model and anomaly outputs, decision and explanation |
| `risk_scores` | Independent 0–100 risk score and contributing factors |
| `fraud_alerts` | Alert lifecycle, severity, customer, transaction, assignment and trigger rules |
| `investigation_cases`, `investigation_notes` | Case lifecycle and investigator evidence notes |
| `audit_logs` | Actor, action, resource, metadata and timestamp |
| `model_versions`, `model_metrics` | Candidate/champion metadata and metrics |
| `drift_reports` | Stored drift findings and affected features |
| `retraining_jobs` | Retraining lifecycle metadata |
| `notification_events` | Durable notification intent/record for alert events |

## Constraints and indexes

- `users.email`, `transactions.transaction_id`, `fraud_alerts.alert_id`, `investigation_cases.case_id`, model version, drift report ID, retraining job ID, and notification event ID are unique.
- Transaction query paths are indexed by transaction/customer/account/merchant/device IDs, event time, and processing/risk state.
- Fraud alert uniqueness on `(transaction_id, alert_type)` stops duplicate same-type alerts for a transaction.
- Foreign keys connect transactions to customer/account/merchant/device masters; prediction, features, risk scores and alerts to transactions; investigation cases to alerts; notes to cases; model metrics to model versions.
- `transactions` is intentionally not partitioned in the local demo. For high volume, partition by event time (e.g. monthly) after selecting an operational retention and archival policy.

Use Alembic rather than `create_all` for controlled deployments:

```bash
cd backend
alembic upgrade head
```

The API still calls `Base.metadata.create_all()` on local startup for first-run convenience. Disable that behavior and require migrations in production.
