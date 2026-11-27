# Deployment guide

## Compose profiles

- Core: PostgreSQL, Redis, single-node Kafka KRaft, FastAPI/consumer, React dashboard.
- `tools`: Kafka UI.
- `mlops`: MLflow and MinIO.
- `observability`: Prometheus and Grafana.
- `orchestration`: Airflow standalone (template only).
- `analytics`: Spark standalone master and worker.

Use `docker compose config` to validate the merged configuration before starting services.

## Environment

Copy `.env.example` to `.env`. The development secrets, user/passwords, and local plaintext endpoints are not suitable for production. Do not commit `.env`, dataset files, or serialized model artifacts.

## API container

The backend image installs the core runtime only. To run XGBoost/LightGBM/SHAP/PyOD/Evidently/MLflow training inside a worker, use the separate `backend/requirements-ml.txt` in a dedicated, pinned ML image. Do not enlarge the hot-path API image with every offline training dependency without an operational reason.

## Database

The app creates tables automatically on first local startup. For controlled deployments, run Alembic migrations as a release job and disable automatic DDL in the application lifespan. Configure encrypted backups, restore testing, connection pooling, retention/archiving, and partition maintenance.

## Network and secrets

Terminate TLS at an approved reverse proxy or ingress. Restrict database, Redis, Kafka, MLflow, MinIO, Prometheus, Grafana, and Airflow ports to private networks. Configure broker authentication/ACLs, Redis authentication/TLS, database least-privilege users, secrets manager, certificate rotation, and audit retention.

## Scaling approach

1. Split FastAPI and Kafka consumer into independent deployments.
2. Scale consumers by Kafka partitions; preserve customer-keyed ordering.
3. Move velocity state to a shared, tested Redis cluster or a dedicated online feature store.
4. Add a schema registry and event compatibility policy.
5. Add PostgreSQL partitioning/read replicas only after query and write profiling.
6. Use batch Spark jobs for backfills and historical aggregation; keep online feature parity tests between batch and serving code.
7. Add OpenTelemetry SDK/exporter and Kafka/Redis/PostgreSQL exporters with SLO-based alerting.
