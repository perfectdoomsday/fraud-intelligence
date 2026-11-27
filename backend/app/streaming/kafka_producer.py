import json
import logging
try:
    from kafka import KafkaProducer
    from kafka.errors import KafkaError
except ImportError:  # Allow API-only development when Kafka is explicitly disabled.
    KafkaProducer = None

    class KafkaError(Exception):
        pass

from app.core.config import settings

logger = logging.getLogger(__name__)


class TransactionPublisher:
    def __init__(self):
        self._producer = None

    def _get_producer(self):
        if not settings.kafka_enabled:
            raise RuntimeError("Kafka publishing is disabled by KAFKA_ENABLED")
        if KafkaProducer is None:
            raise RuntimeError("kafka-python is not installed; install backend/requirements-core.txt")
        if self._producer is None:
            self._producer = KafkaProducer(
                bootstrap_servers=settings.kafka_bootstrap_servers.split(","),
                value_serializer=lambda value: json.dumps(value, default=str).encode("utf-8"),
                key_serializer=lambda key: key.encode("utf-8"),
                acks="all", retries=10,
                max_in_flight_requests_per_connection=1,
                request_timeout_ms=10000, api_version_auto_timeout_ms=10000,
            )
        return self._producer

    def publish(self, payload: dict) -> None:
        producer = self._get_producer()
        try:
            producer.send(settings.kafka_topic_raw, key=payload["customer_id"], value=payload).get(timeout=15)
        except KafkaError:
            logger.exception("Kafka publish failed for transaction %s", payload.get("transaction_id"))
            raise

    def close(self):
        if self._producer is not None:
            self._producer.flush(timeout=5)
            self._producer.close(timeout=5)
            self._producer = None


publisher = TransactionPublisher()
