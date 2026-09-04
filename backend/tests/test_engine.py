from datetime import datetime

from fastapi.testclient import TestClient

from app.ai_engine import MPASInternalAIEngine
from app.integrations import IdempotentWorkOrderPublisher, WorkOrderRequested
from app.main import app
from app.models import Detection, InspectionRequest

client = TestClient(app)


def auth_headers(role: str = "facility_manager") -> dict[str, str]:
    from app.security import create_access_token

    token = create_access_token("u-1", role)
    return {"Authorization": f"Bearer {token}"}


def test_health_reports_ai_engine_ready():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["ai_engine"] == "ready"


def test_image_upload_returns_stored_uri():
    response = client.post(
        "/api/v1/images",
        headers=auth_headers(),
        files={"image": ("trap.jpg", b"fake-jpeg", "image/jpeg")},
    )
    assert response.status_code == 200
    assert response.json()["content_type"] == "image/jpeg"
    assert response.json()["size_bytes"] == 9


def test_token_endpoint_validates_development_credentials():
    invalid = client.post("/api/v1/auth/token", data={"username": "demo", "password": "wrong"})
    valid = client.post("/api/v1/auth/token", data={"username": "demo", "password": "change-me"})
    assert invalid.status_code == 401
    assert valid.status_code == 200
    assert valid.json()["token_type"] == "bearer"


def test_token_endpoint_supports_configured_admin_role(monkeypatch):
    monkeypatch.setenv(
        "MPAS_DEV_ACCOUNTS_JSON",
        '{"admin":{"password":"admin-pass","role":"admin_executive"}}',
    )
    from app.settings import get_settings
    import jwt

    get_settings.cache_clear()
    response = client.post("/api/v1/auth/token", data={"username": "admin", "password": "admin-pass"})
    assert response.status_code == 200
    claims = jwt.decode(response.json()["access_token"], get_settings().jwt_secret, algorithms=[get_settings().jwt_algorithm])
    assert claims["role"] == "admin_executive"
    get_settings.cache_clear()


def test_facility_scope_is_enforced():
    from app.security import create_access_token

    token = create_access_token("scoped-user", "facility_manager", "tenant-1", ["facility-allowed"])
    response = client.get(
        "/api/v1/facilities/facility-forbidden/alert-rule",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_password_helpers_use_argon2id():
    from app.security import hash_password, verify_password

    encoded = hash_password("correct-password")
    assert encoded.startswith("$argon2id$")
    assert verify_password("correct-password", encoded) is True
    assert verify_password("wrong-password", encoded) is False


def test_inspection_creates_work_order_when_threshold_is_reached():
    response = client.post(
        "/api/v1/ai/inspect",
        headers=auth_headers(),
        json={
            "facility_id": "facility-1",
            "trap_id": "trap-9",
            "image_uri": "s3://mpas/images/1.jpg",
            "threshold": 2,
            "detections": [
                {"label": "cockroach", "confidence": 0.91, "area_ratio": 0.02},
                {"label": "cockroach", "confidence": 0.88, "area_ratio": 0.01},
            ],
        },
    )
    assert response.status_code == 200
    assert response.json()["threshold_exceeded"] is True
    assert response.json()["work_order"]["type"] == "pest-treatment"
    assert response.json()["work_order"]["work_order_id"]

    work_orders = client.get("/api/v1/facilities/facility-1/work-orders", headers=auth_headers())
    assert work_orders.status_code == 200
    assert len(work_orders.json()) >= 1
    work_order_id = work_orders.json()[0]["work_order_id"]
    updated = client.patch(
        f"/api/v1/work-orders/{work_order_id}",
        headers=auth_headers("field_technician"),
        json={"status": "in_progress"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "in_progress"
    audit = client.get("/api/v1/audit-events", headers=auth_headers("admin_executive"))
    assert audit.status_code == 200
    assert audit.json()[0]["action"] == "work_order.status_updated"

    forbidden_audit = client.get("/api/v1/audit-events", headers=auth_headers())
    assert forbidden_audit.status_code == 403

    missing = client.patch(
        "/api/v1/work-orders/missing",
        headers=auth_headers(),
        json={"status": "completed"},
    )
    assert missing.status_code == 404


def test_voice_agent_maps_arabic_threshold_request():
    response = client.post(
        "/api/v1/voice/commands",
        headers=auth_headers(),
        json={
            "user_id": "u-1",
            "role": "facility_manager",
            "facility_id": "facility-voice",
            "threshold": 7,
            "transcript": "أنشئ تنبيه عند تجاوز الحد",
        },
    )
    assert response.status_code == 200
    assert response.json()["intent"] == "create_alert_rule"
    assert response.json()["action"]["facility_id"] == "facility-voice"
    assert response.json()["action"]["threshold"] == 7


def test_facility_manager_can_update_alert_rule():
    response = client.put(
        "/api/v1/facilities/facility-1/alert-rule",
        headers=auth_headers(),
        json={"facility_id": "facility-1", "threshold": 9, "cooldown_minutes": 30},
    )
    assert response.status_code == 200
    assert response.json()["threshold"] == 9
    audit = client.get("/api/v1/audit-events", headers=auth_headers("admin_executive"))
    assert audit.status_code == 200
    assert any(event["action"] == "alert_rule.created_or_updated" for event in audit.json())


def test_inspection_uses_saved_facility_threshold():
    update = client.put(
        "/api/v1/facilities/facility-threshold/alert-rule",
        headers=auth_headers(),
        json={"facility_id": "facility-threshold", "threshold": 1},
    )
    assert update.status_code == 200
    response = client.post(
        "/api/v1/ai/inspect",
        headers=auth_headers(),
        json={
            "facility_id": "facility-threshold",
            "trap_id": "trap-1",
            "image_uri": "s3://mpas/image.jpg",
            "detections": [{"label": "fly", "confidence": 0.9, "area_ratio": 0.01}],
        },
    )
    assert response.status_code == 200
    assert response.json()["threshold_exceeded"] is True


def test_field_technician_cannot_update_alert_rule():
    response = client.put(
        "/api/v1/facilities/facility-1/alert-rule",
        headers=auth_headers("field_technician"),
        json={"facility_id": "facility-1", "threshold": 9},
    )
    assert response.status_code == 403


def test_voice_agent_rejects_role_impersonation():
    response = client.post(
        "/api/v1/voice/commands",
        headers=auth_headers("field_technician"),
        json={
            "user_id": "u-1",
            "role": "facility_manager",
            "facility_id": "facility-1",
            "transcript": "أنشئ تنبيه عند تجاوز الحد",
        },
    )
    assert response.status_code == 403


def test_voice_agent_lists_persisted_work_orders():
    response = client.post(
        "/api/v1/voice/commands",
        headers=auth_headers(),
        json={
            "user_id": "u-1",
            "role": "facility_manager",
            "facility_id": "facility-1",
            "transcript": "list work orders",
        },
    )
    assert response.status_code == 200
    assert response.json()["intent"] == "list_work_orders"
    assert isinstance(response.json()["action"]["work_orders"], list)


def test_engine_uses_inference_provider_output():
    engine = MPASInternalAIEngine(
        inference_provider=lambda _: [Detection(label="fly", confidence=0.9, area_ratio=0.01)]
    )
    result = engine.inspect(
        InspectionRequest(facility_id="f-1", trap_id="t-1", image_uri="object://image", threshold=1)
    )
    assert result.pest_count == 1
    assert result.detections[0].label == "fly"


def test_engine_exposes_vision_pipeline_version():
    class Pipeline:
        def analyze(self, image_uri):
            return [Detection(label="ant", confidence=0.8, area_ratio=0.01)], "yolov9-v1+sam2-v1"

    engine = MPASInternalAIEngine(vision_pipeline=Pipeline())
    result = engine.inspect(
        InspectionRequest(facility_id="f-vision", trap_id="t-1", image_uri="object://image")
    )
    assert result.model_version == "yolov9-v1+sam2-v1"
    assert result.pest_count == 1


def test_work_order_publisher_is_idempotent():
    class FakeErp:
        def __init__(self):
            self.calls = 0

        def create_work_order(self, event):
            self.calls += 1
            return "erp-1"

    class FakeNotifications:
        def __init__(self):
            self.calls = 0

        def notify(self, facility_id, event):
            self.calls += 1

    erp = FakeErp()
    notifications = FakeNotifications()
    publisher = IdempotentWorkOrderPublisher(erp, notifications)
    event = WorkOrderRequested("event-1", "f-1", "t-1", 6, 5, "normal", datetime.now())

    assert publisher.publish(event) == "erp-1"
    assert publisher.publish(event) == "erp-1"
    assert erp.calls == 1
    assert notifications.calls == 1
