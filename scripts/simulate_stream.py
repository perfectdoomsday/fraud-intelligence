from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import pandas as pd
from kafka import KafkaProducer

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description="Publish a historical CSV as a live Kafka transaction stream")
    parser.add_argument("--input", type=Path, default=ROOT / "data" / "synthetic_transactions.csv")
    parser.add_argument("--rate", type=float, default=10, help="Events per second")
    parser.add_argument("--broker", default="localhost:29092")
    parser.add_argument("--topic", default="raw-transactions")
    parser.add_argument("--limit", type=int, default=0, help="0 sends all rows")
    args = parser.parse_args()
    if args.rate <= 0:
        raise ValueError("rate must be > 0")
    if not args.input.exists():
        raise FileNotFoundError(f"{args.input} not found; run scripts/generate_data.py first")
    df = pd.read_csv(args.input)
    if args.limit:
        df = df.head(args.limit)
    producer = KafkaProducer(bootstrap_servers=args.broker.split(","),
                             value_serializer=lambda value: json.dumps(value, default=str).encode(),
                             key_serializer=lambda key: key.encode(), acks="all", retries=10)
    interval = 1 / args.rate
    try:
        for row in df.to_dict(orient="records"):
            payload = {k: v for k, v in row.items() if k not in {
                "amount", "log_amount", "transaction_hour", "day_of_week", "is_weekend",
                "transactions_5m", "transactions_1h", "spend_1h", "customer_avg_amount_7d",
                "amount_to_customer_avg", "minutes_since_last_txn", "new_device", "new_location",
                "distance_from_previous_km", "geo_inconsistency", "is_card_not_present", "merchant_risk_rate",
            }}
            producer.send(args.topic, key=str(payload["customer_id"]), value=payload)
            time.sleep(interval)
        producer.flush()
    finally:
        producer.close()
    print(f"Published {len(df)} transactions to {args.topic}")


if __name__ == "__main__":
    main()
