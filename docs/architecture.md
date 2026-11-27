# Architecture and service boundaries

## Deployment shape

The repository uses a modular backend deployment for the local reference stack. The FastAPI process owns HTTP contracts, authentication, read/query endpoints, and the Kafka producer. A managed background thread in the same container owns the Kafka consumer loop. This is deliberate: it minimizes local operational overhead while retaining module boundaries. For scale, run `uvicorn` API replicas without consumers and deploy the `ConsumerWorker` in a separate worker container with an independent replica count.

## Logical services

| Domain service | Module / location | Responsibility | Primary interface |
|---|---|---|---|
| Transaction ingestion | `backend/app/api/transactions.py` | Validate, accept CSV/JSON, publish events | REST + Kafka |
| Streaming | `backend/app/streaming/` | Kafka producer/consumer, offset handling, retries and DLQ | Kafka |
| Feature engineering | `backend/app/services/feature_engineering.py` and `state_store.py` | Point-in-time transaction, velocity, customer and geographic features | Internal Python contract + Redis |
| Fraud inference | `backend/app/services/inference.py` | Load versioned local bundle; return supervised probability + anomaly score | Python service |
| Risk scoring | `backend/app/services/risk_engine.py` | Combine model output and behavioral signals into a bounded 0–100 score | Python service |
| Decision engine | `backend/app/services/decision_engine.py` | Translate risk score/category into allow, monitor, review or escalate | Python service |
| Alert management | `backend/app/api/alerts.py` + processor | Persist/dedupe high-risk alerts and lifecycle state | REST + PostgreSQL |
| Investigations | `backend/app/api/investigations.py` | Cases, notes and audit actions | REST + PostgreSQL |
| Model training | `ml/training/` | Temporal offline training and validation | CLI / Airflow template |
| Model registry | `ModelVersion` + `scripts/register_model.py` | Candidate metadata and promotion decision | PostgreSQL + protected REST |
| Drift monitoring | `ml` and `scripts/check_drift.py` | Feature window comparison and report persistence | CLI / Airflow |
| Notification adapter | `backend/app/services/notification_service.py` | Local alert-notification boundary | Internal Python contract |
| Analytics | `backend/app/api/analytics.py` | Query actual persisted metrics | REST + PostgreSQL |
| Observability | `core/metrics.py`, Prometheus, Grafana | HTTP latency/counts and transaction/alert counters | Prometheus scrape |
| Dashboard | `frontend/` | Operational overview, transaction table, alert/case actions, model and drift views | REST + WebSocket |

## Event contracts

`streaming/schemas/transaction.schema.json` is the first JSON Schema event contract. The active topic is `raw-transactions`; the producer key is `customer_id` to keep a customer's events on one partition. Every consumer still deduplicates by `transaction_id`. For multi-source deployments, use a schema registry and explicit `event_version`, `event_id`, `event_time`, `ingested_at`, producer identity, and correlation ID fields.

The documented downstream topics are defined in `streaming/schemas/topics.md`. The local worker currently consumes the raw topic and commits offsets after database persistence; a processing failure is retried up to three times before a durable write to `dead-letter-transactions`. Add an outbox before using prediction/alert topics as cross-service contracts.

## Feature semantics

- The feature vector is fixed in `backend/app/services/feature_engineering.py::FEATURE_COLUMNS`.
- Redis keeps seven days of customer event amounts, one-hour and five-minute velocity counts, a last-seen location/device state, and expires state keys.
- Events are partitioned by customer to preserve event order within a partition. Late events do not replace a newer last-seen customer pointer; feature windows are bounded by event time.
- The Redis fallback is process-local only. It is useful for a laptop, but is not consistent across replicas and must be disabled or replaced before horizontally scaling workers.
- The current merchant risk-rate and graph relationship fields are placeholders/defaults. Enrich them from validated institution data before relying on them.

## Decision boundary

Model outputs are not business decisions. `inference.py` returns probability/anomaly information. `risk_engine.py` combines model and behavior signals. `decision_engine.py` maps the resulting score into a policy decision. Payment authorization, step-up verification, and holds are not executed by this repository; critical cases create an alert for authorized review.

## Reliability invariants

1. API ingestion returns `202` only after Kafka acknowledges the event.
2. Consumer source offsets are disabled for auto-commit and committed after processing succeeds.
3. Duplicate `transaction_id` events return without generating a second prediction/alert.
4. A failed event is committed only after the DLQ confirms receipt.
5. Transaction, feature, prediction, risk, alert, and notification records are persisted in one database transaction.
6. `estimated_loss_prevented` is null until a defensible counterfactual calculation exists; the dashboard does not invent it.
