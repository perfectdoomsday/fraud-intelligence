"""Small reusable Kafka event publisher for scripts and external producers."""
import json
from kafka import KafkaProducer


class EventProducer:
    def __init__(self, bootstrap_servers: str, topic: str):
        self.topic = topic
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers.split(","),
            value_serializer=lambda payload: json.dumps(payload, default=str).encode("utf-8"),
            key_serializer=lambda key: key.encode("utf-8"), acks="all", retries=10,
        )

    def publish(self, key: str, payload: dict) -> None:
        self.producer.send(self.topic, key=key, value=payload).get(timeout=15)

    def close(self):
        self.producer.flush(timeout=5)
        self.producer.close(timeout=5)
