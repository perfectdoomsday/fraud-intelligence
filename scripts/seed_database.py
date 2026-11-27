"""Publish a synthetic transaction CSV through Kafka (the same path as API ingestion)."""
import argparse
import json
import time
from pathlib import Path

import pandas as pd
from kafka import KafkaProducer

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=ROOT / "data" / "synthetic_transactions.csv")
    parser.add_argument("--broker", default="localhost:29092")
    parser.add_argument("--limit", type=int, default=1000)
    args = parser.parse_args()
    if not args.input.exists():
        raise FileNotFoundError("Run python scripts/generate_data.py first")
    frame = pd.read_csv(args.input).head(args.limit)
    producer = KafkaProducer(bootstrap_servers=args.broker.split(","),
                             value_serializer=lambda value: json.dumps(value, default=str).encode(),
                             key_serializer=lambda key: key.encode(), acks="all", retries=10)
    try:
        for row in frame.to_dict(orient="records"):
            payload = {key: row[key] for key in [
                "transaction_id", "customer_id", "account_id", "amount", "currency", "merchant_id",
                "merchant_category", "timestamp", "payment_method", "device_id", "ip_address",
                "latitude", "longitude", "channel", "transaction_status", "label_is_fraud",
            ]}
            producer.send("raw-transactions", key=payload["customer_id"], value=payload)
        producer.flush()
    finally:
        producer.close()
    print(f"Published {len(frame)} events to raw-transactions")


if __name__ == "__main__":
    main()
