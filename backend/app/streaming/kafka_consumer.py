import json
import logging
import threading

try:
    from kafka import KafkaConsumer, KafkaProducer
    from kafka.errors import KafkaError, NoBrokersAvailable
except ImportError:  # The API can start without the worker in API-only local mode.
    KafkaConsumer = KafkaProducer = None

    class KafkaError(Exception):
        pass

    class NoBrokersAvailable(KafkaError):
        pass

from app.core.config import settings
from app.database.session import SessionLocal
from app.services.transaction_processor import process_transaction
from app.core.metrics import TRANSACTIONS_FAILED

logger = logging.getLogger(__name__)


class ConsumerWorker:
    """At-least-once consumer with bounded retries and a durable dead-letter handoff."""

    def __init__(self):
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self):
        if not settings.kafka_enabled or self._thread is not None:
            return
        if KafkaConsumer is None or KafkaProducer is None:
            logger.error("Kafka worker not started: install kafka-python or set KAFKA_ENABLED=false")
            return
        self._thread = threading.Thread(target=self._run, name="fraud-kafka-consumer", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=10)
            self._thread = None

    def _run(self):
        consumer = producer = None
        while not self._stop.is_set():
            try:
                if producer is None:
                    producer = KafkaProducer(
                        bootstrap_servers=settings.kafka_bootstrap_servers.split(","),
                        value_serializer=lambda value: json.dumps(value, default=str).encode("utf-8"),
                        key_serializer=lambda key: key.encode("utf-8"), acks="all", retries=10,
                    )
                if consumer is None:
                    consumer = KafkaConsumer(
                        settings.kafka_topic_raw,
                        bootstrap_servers=settings.kafka_bootstrap_servers.split(","),
                        group_id=settings.kafka_consumer_group,
                        enable_auto_commit=False,
                        auto_offset_reset="earliest",
                        value_deserializer=lambda data: json.loads(data.decode("utf-8")),
                        max_poll_records=1,
                        consumer_timeout_ms=1000,
                    )
                restart_consumer = False
                for message in consumer:
                    if self._stop.is_set():
                        break
                    success = False
                    last_error = None
                    for attempt in range(1, 4):
                        db = SessionLocal()
                        try:
                            process_transaction(db, message.value)
                            success = True
                            break
                        except Exception as exc:
                            TRANSACTIONS_FAILED.inc()
                            last_error = exc
                            db.rollback()
                            logger.exception("Processing attempt %s/3 failed for %s", attempt,
                                             message.value.get("transaction_id"))
                            self._stop.wait(min(attempt * 1.5, 4))
                        finally:
                            db.close()
                        if self._stop.is_set():
                            break
                    if success:
                        consumer.commit()
                        continue
                    if self._stop.is_set():
                        break
                    # Commit only after the payload is durably written to the DLQ.
                    try:
                        producer.send("dead-letter-transactions", key=message.key.decode() if message.key else None,
                                      value={"source_topic": message.topic, "partition": message.partition,
                                             "offset": message.offset, "payload": message.value,
                                             "error": repr(last_error)}).get(timeout=15)
                        consumer.commit()
                        logger.error("Moved poison event to DLQ: %s", message.value.get("transaction_id"))
                    except Exception:
                        logger.exception("DLQ handoff failed; leaving offset uncommitted for replay")
                        restart_consumer = True
                        break
                if restart_consumer:
                    consumer.close(autocommit=False)
                    consumer = None
            except (NoBrokersAvailable, KafkaError, OSError):
                logger.exception("Kafka consumer unavailable; reconnecting")
                if consumer is not None:
                    consumer.close(autocommit=False)
                    consumer = None
                self._stop.wait(3)
            except Exception:
                logger.exception("Unexpected consumer error")
                if consumer is not None:
                    consumer.close(autocommit=False)
                    consumer = None
                self._stop.wait(3)
        if consumer is not None:
            consumer.close(autocommit=False)
        if producer is not None:
            producer.flush(timeout=5)
            producer.close(timeout=5)


consumer_worker = ConsumerWorker()
