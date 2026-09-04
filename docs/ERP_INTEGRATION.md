# ERP and cloud integration contract

## Event envelope

```json
{
  "eventType": "WorkOrderRequested",
  "eventId": "facility-1:trap-9:2026-09-04T12:00:00Z:yolov9-v1",
  "tenantId": "tenant-1",
  "facilityId": "facility-1",
  "occurredAt": "2026-09-04T12:00:00Z",
  "payload": {"trapId": "trap-9", "pestCount": 6, "threshold": 5, "priority": "normal"}
}
```

## Alert threshold

The API accepts a per-inspection `threshold`. A production alert-rule table should override this per tenant, facility, pest type, and trap group. Alert rules should support cooldown windows, escalation recipients, and acknowledgment state to prevent notification storms.

## Required adapters

- `ObjectStorage`: `put_image`, `get_signed_url`, `put_model_artifact`.
- `InferenceProvider`: `detect_yolov9`, `segment_sam2`, `model_version`.
- `ErpClient`: `create_work_order`, `update_work_order`, `get_work_order`.
- `NotificationProvider`: push, email, SMS, and voice-agent confirmation.

Each adapter must expose timeout, retry, idempotency, and structured error metrics.

The backend implementation provides these boundaries in `backend/app/integrations.py`. `WorkOrderRequested` is the internal event contract and `IdempotentWorkOrderPublisher` records the event key before notifying downstream systems. Replace its in-memory map with a durable outbox table or queue consumer before deploying multiple API replicas.

M-PAS exposes `PATCH /api/v1/work-orders/{work_order_id}` for operational status changes: `requested`, `acknowledged`, `in_progress`, `completed`, and `cancelled`. The same status should be mapped to the external ERP status by the adapter and retained in the local audit trail.
