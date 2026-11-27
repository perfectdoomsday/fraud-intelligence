# API and contract notes

Base path: `/api/v1`. Interactive OpenAPI docs: `http://localhost:8000/docs`.

## Authentication

`POST /auth/token` uses OAuth2 password form fields `username` and `password` and returns `access_token`, `token_type`, `role`, and `expires_in`. Send the token as `Authorization: Bearer <token>` on protected routes.

## Request shapes

### Transaction event

```json
{
  "transaction_id": "TXN-1001",
  "customer_id": "CUS-101",
  "account_id": "ACC-101",
  "amount": 8200.5,
  "currency": "INR",
  "merchant_id": "MER-42",
  "merchant_category": "electronics",
  "timestamp": "2026-11-27T10:30:00+05:30",
  "payment_method": "card",
  "device_id": "DEV-22",
  "ip_address": "203.0.113.10",
  "latitude": 28.6139,
  "longitude": 77.209,
  "channel": "ecommerce",
  "transaction_status": "completed"
}
```

Unknown fields are rejected by the transaction Pydantic schema. Timestamps should include a timezone offset. Amounts must be positive and bounded. Currency is normalized to uppercase.

### Ingestion response

`POST /transactions` returns `202 Accepted` and `{ "status": "queued", "transaction_id": "..." }` only after the broker acknowledges the message. It can return `503` if the broker is unavailable. The durable scored result appears in `GET /transactions/{transaction_id}` after the consumer completes.

### Alert state transitions

`PATCH /alerts/{alert_id}/status` accepts `ACKNOWLEDGED`, `INVESTIGATING`, `CONFIRMED_FRAUD`, `FALSE_POSITIVE`, or `CLOSED`. Changes are audit-logged. `POST /alerts/{alert_id}/assign` assigns the alert to an investigator identifier/email. An institution should add user-directory validation and allowed transition guards.

### Investigation case

`POST /cases` accepts `alert_id`, `title`, and optional `assigned_to`. `POST /cases/{case_id}/notes` accepts a bounded `note` string and captures the current actor from the JWT.

## Error conventions

FastAPI returns standard JSON errors with `detail` text. Common statuses are `401` for absent/invalid credentials, `403` for insufficient role permissions, `404` for missing resources, `413` for payload size limits, `415` for non-CSV uploads, `422` for schema validation, and `503` when Kafka cannot acknowledge an ingestion event.

The CSV uploader accepts UTF-8 CSV up to 20 MB and reports accepted transaction IDs plus row-level rejected records. The upload schema only forwards event fields; offline feature columns and labels are not used as runtime model features.
