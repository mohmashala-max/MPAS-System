# M-PAS

Industrial pest-management platform foundation for multi-tenant facilities, smart traps, AI inspections, field operations, and ERP work orders.

## Run the backend

```bash
python -m pip install -e 'backend[test]'
python -m uvicorn app.main:app --app-dir backend --reload
```

Container build and run:

```bash
docker build -f backend/Dockerfile -t mpas-backend:dev backend
docker run --rm -p 8000:8000 mpas-backend:dev
```

Run the persistent local stack:

```bash
docker compose up --build
```

The `mpas-data` volume preserves alert rules, work orders, audit events, and uploaded images across container restarts.

CI workflows are defined in `.github/workflows/backend.yml`, `.github/workflows/android.yml`, and `.github/workflows/windows.yml`. The Android workflow publishes `app-debug.apk`, and the Windows workflow publishes `MPAS.Desktop.exe` as build artifacts. Windows CI runs on a native Windows runner.

Copy `backend/.env.example` to `backend/.env` for local configuration. The development login defaults to `demo` / `change-me`; change both values immediately. Additional local roles can be configured through `MPAS_DEV_ACCOUNTS_JSON`, whose accounts may include `tenant_id` and a `facilities` allow-list (`["*"]` for local unrestricted access). Alert rules persist in SQLite at `MPAS_ALERT_DATABASE_PATH`. In production, use a managed database and inject `MPAS_JWT_SECRET` from a secret manager; also replace development accounts with a tenant user repository, Argon2id, MFA, and OAuth2 PKCE.

Health check: `GET /health`. The API exposes OAuth2 bearer-token scaffolding, image upload at `POST /api/v1/images`, `POST /api/v1/ai/inspect`, `POST /api/v1/voice/commands`, facility alert rules at `PUT/GET /api/v1/facilities/{facility_id}/alert-rule`, work-order listing at `GET /api/v1/facilities/{facility_id}/work-orders`, status updates at `PATCH /api/v1/work-orders/{work_order_id}`, and executive audit logs at `GET /api/v1/audit-events`. The token endpoint is intentionally a development seam and must be replaced by a tenant user repository, Argon2id verification, MFA, and a managed signing key before production.

## Validate

```bash
python -m pytest backend/tests -q
```

Common project commands are available through `Makefile`:

```bash
make test      # backend tests
make build     # Docker image
make android   # Android debug APK
make windows   # Windows self-contained EXE
make windows-package # Windows EXE plus usage guide ZIP
make up        # Compose stack, waits for health
make down      # stop Compose stack
```

Android build (requires Android SDK, API 35, and `ANDROID_HOME`):

```bash
./android/gradlew -p android assembleDebug
```

The field core is configured for Android 7.0+ (`minSdk 24`).

## Repository map

- `backend/app/ai_engine.py`: MPAS Internal AI Engine decision boundary.
- `backend/app/inference.py`: YOLOv9/SAM2 adapter contract and model-version pipeline.
- `android/app/src/main/java/com/mpas/mobile`: Room queue and WorkManager sync core.
- `ios/MpasField`: Swift offline queue, OAuth2 client, image upload, retrying sync coordinator, and `NWPathMonitor` connectivity trigger.
- `docs/ARCHITECTURE.md`: deployment, tenancy, security, voice-agent, and scale plan.
- `docs/ERP_INTEGRATION.md`: threshold alerts, event envelope, and ERP adapter contract.

YOLOv9, SAM2, object storage, ERP, ASR/TTS, and notifications are adapter boundaries in this initial implementation. Their production connectors require selected vendors, credentials, model artifacts, and benchmark data.

The iOS source requires an Xcode project and iOS SDK on macOS for device packaging; the Linux container validates the shared API contract but cannot produce an iOS archive.

Windows client: `windows/dist/MPAS.Desktop.exe`. Copy the executable to a Windows 10/11 machine, start the Backend with Docker Compose, and set the API URL to the reachable server address if it is not `http://localhost:8000/`. See [windows/README.md](windows/README.md) for the complete client guide.