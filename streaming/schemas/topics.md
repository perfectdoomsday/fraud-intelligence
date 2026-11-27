# Kafka topics

| Topic | Key | Purpose | Retention guidance |
|---|---|---|---|
| `raw-transactions` | `customer_id` (partition affinity); deduplicate by `transaction_id` | API-ingested transaction events | 7 days in local demo |
| `validated-transactions` | `transaction_id` | Reserved for validated/enriched event separation | Configure per compliance policy |
| `enriched-transactions` | `transaction_id` | Feature-enriched transaction events | Configure per compliance policy |
| `fraud-predictions` | `transaction_id` | Model/risk outputs | 7 days in local demo |
| `high-risk-transactions` | `transaction_id` | High/critical events | 30 days in local demo |
| `fraud-alerts` | `alert_id` | Alert lifecycle events | 30 days in local demo |
| `model-monitoring-events` | `event_id` | Drift and quality signals | 30 days in local demo |
| `dead-letter-transactions` | `transaction_id` | Events that exceed bounded retries | Do not auto-delete in production |

The local implementation actively uses `raw-transactions` as the durable work queue. The remaining topics are documented integration boundaries; add a schema registry, bounded retry topic, and operational DLQ replay process before production use.
