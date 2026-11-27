# Consumer contract

The actively deployed consumer is `backend/app/streaming/kafka_consumer.py`. It uses explicit offset commits, one-record polls, bounded retries, and a DLQ handoff. Keep processing idempotent by `transaction_id`; use the producer's `customer_id` partition key for rolling behavioural state. If the consumer is extracted to its own container, set `KAFKA_ENABLED=false` in the API deployment and run a dedicated worker entrypoint.
