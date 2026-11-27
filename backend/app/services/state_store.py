import json
import logging
import time
from collections import defaultdict, deque
from threading import Lock

from app.core.config import settings

logger = logging.getLogger(__name__)


class TransactionStateStore:
    """Low-latency velocity state in Redis, with an in-process demo fallback."""

    def __init__(self):
        self.client = None
        self._lock = Lock()
        self._events: dict[str, deque] = defaultdict(deque)
        self._devices: dict[str, set[str]] = defaultdict(set)
        self._last: dict[str, dict] = {}
        try:
            import redis
            client = redis.Redis.from_url(settings.redis_url, decode_responses=True, socket_timeout=1)
            client.ping()
            self.client = client
        except Exception as exc:
            logger.warning("Redis unavailable; using process-local demo state: %s", exc)

    def update_and_get(self, tx: dict) -> dict:
        customer = tx["customer_id"]
        device = tx["device_id"]
        event_ts = tx["timestamp"]
        if hasattr(event_ts, "timestamp"):
            now = event_ts.timestamp()
        else:
            from datetime import datetime
            now = datetime.fromisoformat(str(event_ts).replace("Z", "+00:00")).timestamp()
        if self.client:
            return self._redis_update(customer, device, tx, now)
        return self._memory_update(customer, device, tx, now)

    def _redis_update(self, customer, device, tx, now):
        key = f"fraud:customer:{customer}:events"
        devices_key = f"fraud:customer:{customer}:devices"
        pipe = self.client.pipeline()
        pipe.zremrangebyscore(key, 0, now - 7 * 86400)
        pipe.zcount(key, now - 300, now)
        pipe.zcount(key, now - 3600, now)
        pipe.zrangebyscore(key, now - 7 * 86400, now)
        pipe.zrangebyscore(key, now - 3600, now)
        pipe.sismember(devices_key, device)
        previous_raw = self.client.get(f"fraud:customer:{customer}:last")
        result = pipe.execute()
        seven_day_events = [json.loads(item) for item in result[3]]
        one_hour_events = [json.loads(item) for item in result[4]]
        average_values = [item["amount"] for item in seven_day_events]
        previous = json.loads(previous_raw) if previous_raw else None
        if previous and previous["ts"] > now:
            previous = None  # Late event: do not compare it to a future transaction.
        elapsed = max(0.0, (now - previous["ts"]) / 60) if previous else 1440
        state = {
            "transactions_5m": result[1], "transactions_1h": result[2],
            "spend_1h": sum(item["amount"] for item in one_hour_events),
            "customer_avg_amount_7d": (sum(average_values) / len(average_values)) if average_values else tx["amount"],
            "minutes_since_last_txn": elapsed, "new_device": not bool(result[5]),
            "new_location": previous is None or previous.get("lat") != tx.get("latitude") or previous.get("lon") != tx.get("longitude"),
            "previous_location": {"latitude": previous.get("lat"), "longitude": previous.get("lon")} if previous else {},
        }
        payload = json.dumps({"transaction_id": tx["transaction_id"], "amount": tx["amount"]})
        self.client.zadd(key, {payload: now})
        self.client.expire(key, 7 * 86400)
        self.client.sadd(devices_key, device)
        self.client.expire(devices_key, 30 * 86400)
        if previous_raw is None or json.loads(previous_raw).get("ts", 0) <= now:
            self.client.setex(f"fraud:customer:{customer}:last", 30 * 86400,
                              json.dumps({"ts": now, "lat": tx.get("latitude"), "lon": tx.get("longitude")}))
        return state

    def _memory_update(self, customer, device, tx, now):
        with self._lock:
            events = deque(item for item in self._events[customer] if now - 7 * 86400 <= item[0] <= now)
            self._events[customer] = events
            one_hour = [item for item in events if item[0] >= now - 3600]
            five_min = [item for item in events if item[0] >= now - 300]
            stored_previous = self._last.get(customer)
            previous = stored_previous if not stored_previous or stored_previous["ts"] <= now else None
            state = {
                "transactions_5m": len(five_min), "transactions_1h": len(one_hour),
                "spend_1h": sum(item[1] for item in one_hour),
                "customer_avg_amount_7d": sum(item[1] for item in events) / len(events) if events else tx["amount"],
                "minutes_since_last_txn": max(0.0, (now - previous["ts"]) / 60) if previous else 1440,
                "new_device": int(device not in self._devices[customer]),
                "new_location": int(previous is None or previous.get("lat") != tx.get("latitude") or previous.get("lon") != tx.get("longitude")),
                "previous_location": {"latitude": previous.get("lat"), "longitude": previous.get("lon")} if previous else {},
            }
            events.append((now, float(tx["amount"])))
            self._devices[customer].add(device)
            if stored_previous is None or stored_previous["ts"] <= now:
                self._last[customer] = {"ts": now, "lat": tx.get("latitude"), "lon": tx.get("longitude")}
            return state
