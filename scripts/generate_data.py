from __future__ import annotations

import argparse
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.services.feature_engineering import FEATURE_COLUMNS  # noqa: E402

MERCHANT_CATEGORIES = ["grocery", "electronics", "travel", "fuel", "food_delivery", "fashion", "gaming", "other"]
CHANNELS = ["online", "pos", "mobile", "ecommerce"]
PAYMENT_METHODS = ["card", "upi", "wallet", "net_banking"]


def generate_transactions(n: int = 20000, fraud_rate: float = 0.012, seed: int = 42) -> pd.DataFrame:
    if n < 100 or not 0 < fraud_rate < 0.5:
        raise ValueError("Use n >= 100 and fraud_rate between 0 and 0.5")
    rng = np.random.default_rng(seed)
    random.seed(seed)
    start = datetime.now(timezone.utc) - timedelta(days=45)
    rows = []
    customers = [f"CUS-{i:05d}" for i in range(max(100, n // 12))]
    customer_avg = {c: float(rng.lognormal(7.1, 0.75)) for c in customers}
    customer_devices = {c: f"DEV-{rng.integers(1, 10000):05d}" for c in customers}
    previous_location = {c: (float(rng.uniform(8, 28)), float(rng.uniform(68, 89))) for c in customers}
    for i in range(n):
        customer = customers[int(rng.integers(0, len(customers)))]
        ts = start + timedelta(seconds=int(i * (45 * 86400 / n)))
        fraud = bool(rng.random() < fraud_rate)
        avg = customer_avg[customer]
        amount = float(rng.lognormal(np.log(max(avg, 10)), 0.55))
        transactions_5m = int(rng.poisson(0.15))
        transactions_1h = int(rng.poisson(0.8))
        device = customer_devices[customer]
        new_device = int(rng.random() < 0.025)
        new_location = int(rng.random() < 0.04)
        lat, lon = previous_location[customer]
        if new_location:
            lat, lon = float(rng.uniform(8, 28)), float(rng.uniform(68, 89))
        merchant_category = random.choice(MERCHANT_CATEGORIES)
        channel = random.choice(CHANNELS)
        merchant_risk_rate = float(rng.beta(1.5, 40))
        distance = float(rng.uniform(0, 25))
        elapsed = float(rng.uniform(30, 1440))
        if fraud:
            pattern = int(rng.integers(0, 4))
            if pattern == 0:  # high-value/card-not-present
                amount = avg * float(rng.uniform(5, 15))
                channel = "ecommerce"
            elif pattern == 1:  # velocity
                transactions_5m = int(rng.integers(4, 10))
                transactions_1h = int(rng.integers(7, 18))
                amount = avg * float(rng.uniform(1.5, 4))
            elif pattern == 2:  # device takeover
                new_device, new_location = 1, 1
                amount = avg * float(rng.uniform(2, 9))
            else:  # merchant/geographic anomaly
                merchant_risk_rate = float(rng.uniform(0.18, 0.65))
                distance = float(rng.uniform(700, 5000))
                elapsed = float(rng.uniform(1, 15))
                lat, lon = float(rng.uniform(8, 28)), float(rng.uniform(68, 89))
        features = {
            "amount": amount,
            "log_amount": float(np.log1p(amount)),
            "transaction_hour": float(ts.hour),
            "day_of_week": float(ts.weekday()),
            "is_weekend": float(ts.weekday() >= 5),
            "transactions_5m": float(transactions_5m),
            "transactions_1h": float(transactions_1h),
            "spend_1h": float(amount * max(transactions_1h, 1)),
            "customer_avg_amount_7d": float(avg),
            "amount_to_customer_avg": float(amount / max(avg, 1)),
            "minutes_since_last_txn": elapsed,
            "new_device": float(new_device),
            "new_location": float(new_location),
            "distance_from_previous_km": distance,
            "geo_inconsistency": float(distance > elapsed * 1.5),
            "is_card_not_present": float(channel in {"online", "ecommerce", "mobile"}),
            "merchant_risk_rate": merchant_risk_rate,
        }
        row = {
            "transaction_id": f"TXN-{i + 1:09d}", "customer_id": customer,
            "account_id": f"ACC-{customer[4:]}", "amount": round(amount, 2), "currency": "INR",
            "merchant_id": f"MER-{int(rng.integers(1, 600)):04d}", "merchant_category": merchant_category,
            "timestamp": ts.isoformat(), "payment_method": random.choice(PAYMENT_METHODS),
            "device_id": f"DEV-NEW-{i}" if new_device else device, "ip_address": f"10.{int(rng.integers(0,255))}.{int(rng.integers(0,255))}.{int(rng.integers(1,254))}",
            "latitude": round(lat, 5), "longitude": round(lon, 5), "channel": channel,
            "transaction_status": "completed", "label_is_fraud": int(fraud),
        }
        row.update(features)
        rows.append(row)
    frame = pd.DataFrame(rows)
    # Preserve chronology; labels remain synthetic ground truth for offline experiments only.
    return frame.sort_values("timestamp").reset_index(drop=True)


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic transaction data")
    parser.add_argument("--rows", type=int, default=20000)
    parser.add_argument("--fraud-rate", type=float, default=0.012)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "synthetic_transactions.csv")
    args = parser.parse_args()
    df = generate_transactions(args.rows, args.fraud_rate, args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.output, index=False)
    print(f"Wrote {len(df):,} transactions to {args.output}; synthetic fraud prevalence={df.label_is_fraud.mean():.3%}")


if __name__ == "__main__":
    main()
