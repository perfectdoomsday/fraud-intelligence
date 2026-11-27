"""Notification boundary; log locally, replace with institution-approved delivery adapters."""
import logging

logger = logging.getLogger(__name__)


def send_alert_notification(alert_id: str, severity: str, transaction_id: str) -> None:
    logger.info("notification_event", extra={"alert_id": alert_id, "severity": severity,
                                             "transaction_id": transaction_id,
                                             "channel": "local-log-adapter"})
