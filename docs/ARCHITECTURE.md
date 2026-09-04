# M-PAS implementation blueprint

## Runtime boundaries

- `backend/app/ai_engine.py` is the MPAS Internal AI Engine orchestration boundary.
- `backend/app/inference.py` defines `MpasVisionPipeline`: a production adapter injects YOLOv9 detection and SAM2 segmentation, maps output to `Detection`, and propagates a combined model version into the inspection result.
- FastAPI remains stateless; tenant and facility scope must be enforced from the OAuth2 token before database access.
- JWTs carry `tenant_id` and a `facilities` allow-list. Facility-scoped routes reject requests outside that list; production identity providers must issue these claims from the tenant membership service.
- Cloud object storage stores original images and model artifacts. Database records keep URI, checksum, model version, and audit metadata.
- Development accepts images through `POST /api/v1/images` and stores them under `MPAS_IMAGE_STORAGE_PATH`; production must replace this filesystem adapter with encrypted S3/Azure Blob/GCS storage and signed URLs.

## Voice agent

The voice client captures audio, sends a transcript plus locale to `POST /api/v1/voice/commands`, and renders the returned intent/action only after role authorization. Production voice transport should use a streaming ASR/TTS provider behind an adapter. The command router must use allow-listed intents, confirmation for destructive actions, and an audit event for every action.

Supported initial intent families: `create_alert_rule`, `list_work_orders`, and inspection/work-order creation. `list_work_orders` requires `facility_id` and returns the persisted work-order records for that facility. Arabic, English, French, and Spanish utterances are accepted by the contract; add locale-specific NLU tests before enabling autonomous execution.
Alert rules are managed through `PUT /api/v1/facilities/{facility_id}/alert-rule` and read through `GET /api/v1/facilities/{facility_id}/alert-rule`. They persist in the local SQLite store for development and must move to the managed tenant database in production. A voice command that creates a rule must include `facility_id` and is executed only when the JWT role matches the command role. Only `admin_executive` and `facility_manager` may update rules; field technicians can inspect and synchronize field observations but cannot change facility policy.

## Security and tenancy

Use OAuth2 Authorization Code + PKCE for user applications, short-lived access tokens, refresh-token rotation, MFA for admin/executive users, and Argon2id for password storage in production. Inject `MPAS_JWT_SECRET` through a secret manager; never use the development default. Enforce tenant and facility IDs in repository queries, encrypt cloud storage with AES-256/KMS, require TLS 1.3, and emit immutable audit logs. The included `security.py` is a dependency-light development seam, not a compliance implementation.

## Scale target

For 20 facilities, 10,000 traps, and 1,000,000 readings/day: ingest through a queue, batch writes, partition telemetry by tenant/time, use object storage for images, and autoscale inference workers separately from the API. Keep p95 API latency and image inference latency as explicit SLO metrics; the stated 80ms/150ms targets require benchmark data on the selected deployment hardware.

## ERP workflow

1. Persist a threshold event with idempotency key `facility_id:trap_id:event_time:model_version`.
2. Publish `WorkOrderRequested` to the integration queue.
3. ERP adapter maps it to SAP/Oracle APIs and stores the external ID.
4. Retry with exponential backoff; dead-letter failures for operations review.
5. Consume status changes back into M-PAS and notify the facility manager.

Never call ERP synchronously from image inference. This preserves inspection latency and prevents duplicate work orders.

Sensitive operational changes, including alert-rule mutations from REST or Voice Agent and work-order status changes, are written to the SQLite audit store during development and exposed only to `admin_executive` through `GET /api/v1/audit-events`. Production deployments should stream these immutable events to the tenant audit platform or SIEM.
