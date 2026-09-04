from pathlib import Path
import json
from uuid import uuid4

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, status
from fastapi.security import OAuth2PasswordRequestForm

from .ai_engine import MPASInternalAIEngine
from hashlib import sha256

from .models import AlertRule, AuditEvent, ImageUploadResponse, InspectionRequest, InspectionResult, UserRole, VoiceCommand, VoiceCommandResult, WorkOrder, WorkOrderStatusUpdate
from .security import access_claims, create_access_token, require_access_token, require_role
from .settings import get_settings
from .store import AlertRuleStore

app = FastAPI(title="M-PAS Platform API", version="0.1.0")
engine = MPASInternalAIEngine()
alert_store = AlertRuleStore(get_settings().alert_database_path)


def require_facility_access(claims: dict[str, object], facility_id: str) -> None:
    facilities = claims.get("facilities", ["*"])
    if "*" not in facilities and facility_id not in facilities:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Facility is outside tenant scope")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "mpas-api", "ai_engine": "ready"}


@app.post("/api/v1/images", response_model=ImageUploadResponse)
async def upload_image(
    image: UploadFile = File(...),
    _: str = Depends(require_access_token),
) -> ImageUploadResponse:
    settings = get_settings()
    if image.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Unsupported image type")
    target_directory = Path(settings.image_storage_path)
    target_directory.mkdir(parents=True, exist_ok=True)
    target = target_directory / f"{uuid4().hex}.upload"
    size = 0
    with target.open("wb") as destination:
        while chunk := await image.read(1024 * 1024):
            size += len(chunk)
            if size > settings.max_image_bytes:
                target.unlink(missing_ok=True)
                raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Image too large")
            destination.write(chunk)
    return ImageUploadResponse(image_uri=str(target), content_type=image.content_type, size_bytes=size)


@app.post("/api/v1/auth/token")
def token(form: OAuth2PasswordRequestForm = Depends()) -> dict[str, str]:
    settings = get_settings()
    try:
        accounts = json.loads(settings.dev_accounts_json)
    except json.JSONDecodeError as error:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Invalid account configuration") from error
    account = accounts.get(form.username)
    if account is None and form.username == settings.dev_username:
        account = {
            "password": settings.dev_password,
            "role": "facility_manager",
            "tenant_id": "tenant-development",
            "facilities": ["*"],
        }
    if account is None or account.get("password") != form.password or account.get("role") not in {role.value for role in UserRole}:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    # Replace with the tenant user repository and Argon2id verification before production.
    return {
        "access_token": create_access_token(
            form.username,
            account["role"],
            account.get("tenant_id", "tenant-development"),
            account.get("facilities", ["*"]),
        ),
        "token_type": "bearer",
    }


@app.post("/api/v1/ai/inspect", response_model=InspectionResult)
def inspect(request: InspectionRequest, claims: dict[str, object] = Depends(access_claims)) -> InspectionResult:
    require_facility_access(claims, request.facility_id)
    saved_rule = alert_store.get(request.facility_id)
    if request.threshold is None and saved_rule is not None and saved_rule.enabled:
        request = request.model_copy(update={"threshold": saved_rule.threshold})
    result = engine.inspect(request)
    if result.work_order:
        work_order_id = sha256(
            f"{request.facility_id}:{request.trap_id}:{request.image_uri}:{result.pest_count}".encode()
        ).hexdigest()[:24]
        result.work_order = {
            **result.work_order,
            "work_order_id": work_order_id,
        }
        alert_store.save_work_order(
            WorkOrder(
                work_order_id=work_order_id,
                facility_id=request.facility_id,
                trap_id=request.trap_id,
                pest_count=result.pest_count,
                priority=str(result.work_order["priority"]),
            )
        )
    return result


@app.post("/api/v1/voice/commands", response_model=VoiceCommandResult)
def voice_command(command: VoiceCommand, claims: dict[str, object] = Depends(access_claims)) -> VoiceCommandResult:
    if claims.get("role") != command.role.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role does not match token")
    result = engine.handle_voice(command)
    if command.facility_id:
        require_facility_access(claims, command.facility_id)
    if result.intent == "list_work_orders":
        if not command.facility_id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="facility_id is required")
        result.action = {
            "type": "list_work_orders",
            "facility_id": command.facility_id,
            "work_orders": [item.model_dump() for item in alert_store.list_work_orders(command.facility_id)],
        }
        alert_store.audit(claims["sub"], "work_order.listed", command.facility_id, {"source": "voice"})
        return result
    if result.intent == "create_alert_rule":
        if command.role not in (UserRole.ADMIN_EXECUTIVE, UserRole.FACILITY_MANAGER):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role cannot update alert rules")
        if not command.facility_id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="facility_id is required")
        rule = AlertRule(
            facility_id=command.facility_id,
            threshold=int(result.action["threshold"]),
        )
        alert_store.upsert(rule)
        alert_store.audit(
            claims["sub"],
            "alert_rule.created_or_updated",
            command.facility_id,
            {"threshold": rule.threshold, "source": "voice"},
        )
        result.action = {**(result.action or {}), "facility_id": command.facility_id}
    return result


@app.put("/api/v1/facilities/{facility_id}/alert-rule", response_model=AlertRule)
def upsert_alert_rule(
    facility_id: str,
    rule: AlertRule,
    claims: dict[str, str] = Depends(require_role(UserRole.ADMIN_EXECUTIVE, UserRole.FACILITY_MANAGER)),
) -> AlertRule:
    require_facility_access(claims, facility_id)
    if rule.facility_id != facility_id:
        rule = rule.model_copy(update={"facility_id": facility_id})
    alert_store.upsert(rule)
    alert_store.audit(
        claims["sub"],
        "alert_rule.created_or_updated",
        facility_id,
        {"threshold": rule.threshold, "source": "rest"},
    )
    return rule


@app.get("/api/v1/facilities/{facility_id}/alert-rule", response_model=AlertRule)
def get_alert_rule(
    facility_id: str,
    claims: dict[str, object] = Depends(access_claims),
) -> AlertRule:
    require_facility_access(claims, facility_id)
    return alert_store.get(facility_id) or AlertRule(facility_id=facility_id)


@app.get("/api/v1/facilities/{facility_id}/work-orders", response_model=list[WorkOrder])
def list_work_orders(
    facility_id: str,
    claims: dict[str, object] = Depends(access_claims),
) -> list[WorkOrder]:
    require_facility_access(claims, facility_id)
    return alert_store.list_work_orders(facility_id)


@app.patch("/api/v1/work-orders/{work_order_id}", response_model=WorkOrder)
def update_work_order(
    work_order_id: str,
    update: WorkOrderStatusUpdate,
    claims: dict[str, object] = Depends(require_role(
        UserRole.ADMIN_EXECUTIVE, UserRole.FIELD_TECHNICIAN, UserRole.FACILITY_MANAGER
    )),
) -> WorkOrder:
    work_order = alert_store.update_work_order_status(work_order_id, update.status)
    if work_order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work order not found")
    require_facility_access(claims, work_order.facility_id)
    alert_store.audit(claims["sub"], "work_order.status_updated", work_order_id, {"status": update.status})
    return work_order


@app.get("/api/v1/audit-events", response_model=list[AuditEvent])
def audit_events(
    _: dict[str, str] = Depends(require_role(UserRole.ADMIN_EXECUTIVE)),
) -> list[AuditEvent]:
    return alert_store.list_audit_events()
