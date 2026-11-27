from prometheus_client import Counter, Histogram

HTTP_REQUESTS = Counter(
    "fraud_http_requests_total", "HTTP requests received", ["method", "route", "status"]
)
HTTP_REQUEST_DURATION = Histogram(
    "fraud_http_request_duration_seconds", "HTTP request duration", ["method", "route"]
)
TRANSACTIONS_PROCESSED = Counter("fraud_transactions_processed_total", "Processed transaction events")
TRANSACTIONS_FAILED = Counter("fraud_transactions_failed_total", "Failed transaction processing attempts")
ALERTS_CREATED = Counter("fraud_alerts_created_total", "Fraud alerts created", ["severity"])
