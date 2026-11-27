# Monitoring extensions

Prometheus scrapes the API's `/api/v1/metrics` endpoint. Current custom metrics cover HTTP request count/duration, transaction processing count, processing failures (counter reserved for worker instrumentation), and fraud alerts by severity. Grafana provisioning contains a starter API dashboard.

Before production, add Kafka consumer lag, Redis command latency/memory, PostgreSQL pool/lock health, ML inference latency/model version, queue age, drift/quality reports, and business metrics with strict label-cardinality controls. Add OpenTelemetry traces and propagate correlation IDs across REST, Kafka and database boundaries.
