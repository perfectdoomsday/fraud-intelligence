"""Basic API load test. Set FRAUD_TOKEN and run: locust -f locustfile.py --host http://localhost:8000"""
import os
import uuid
from datetime import datetime, timezone
from locust import HttpUser, between, task


class FraudAPIUser(HttpUser):
    wait_time = between(0.05, 0.5)

    def on_start(self):
        self.token = os.getenv("FRAUD_TOKEN", "")
        self.headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}

    @task(4)
    def dashboard_overview(self):
        self.client.get("/api/v1/analytics/overview", headers=self.headers, name="GET overview")

    @task(3)
    def list_transactions(self):
        self.client.get("/api/v1/transactions?page=1&page_size=25", headers=self.headers, name="GET transactions")

    @task(2)
    def list_alerts(self):
        self.client.get("/api/v1/alerts", headers=self.headers, name="GET alerts")

    @task(1)
    def ingest_transaction(self):
        customer = f"CUS-LOAD-{uuid.uuid4().hex[:8]}"
        payload = {
            "transaction_id": f"TXN-LOAD-{uuid.uuid4().hex}", "customer_id": customer,
            "account_id": f"ACC-{customer}", "amount": 1200.0, "currency": "INR",
            "merchant_id": "MER-LOAD-1", "merchant_category": "grocery",
            "timestamp": datetime.now(timezone.utc).isoformat(), "payment_method": "card",
            "device_id": "DEV-LOAD-1", "ip_address": "198.51.100.10", "channel": "online",
            "transaction_status": "completed",
        }
        self.client.post("/api/v1/transactions", json=payload, headers=self.headers, name="POST transaction")
