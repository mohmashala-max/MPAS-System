from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class UserRole(StrEnum):
    ADMIN_EXECUTIVE = "admin_executive"
    FIELD_TECHNICIAN = "field_technician"
    FACILITY_MANAGER = "facility_manager"


class Detection(BaseModel):
    label: str
    confidence: float = Field(ge=0, le=1)
    area_ratio: float = Field(ge=0, le=1)
    source: str = "internal-ai-engine"


class InspectionRequest(BaseModel):
    facility_id: str
    trap_id: str
    image_uri: str
    detections: list[Detection] = Field(default_factory=list)
    threshold: int | None = Field(default=None, ge=1)


class ImageUploadResponse(BaseModel):
    image_uri: str
    content_type: str
    size_bytes: int


class AlertRule(BaseModel):
    facility_id: str
    pest_type: str = "any"
    threshold: int = Field(default=5, ge=1)
    cooldown_minutes: int = Field(default=60, ge=1)
    enabled: bool = True


class InspectionResult(BaseModel):
    facility_id: str
    trap_id: str
    detections: list[Detection]
    pest_count: int
    threshold_exceeded: bool
    work_order: dict[str, Any] | None = None
    model_version: str | None = None


class WorkOrder(BaseModel):
    work_order_id: str
    facility_id: str
    trap_id: str
    pest_count: int
    priority: str
    status: str = "requested"


class WorkOrderStatusUpdate(BaseModel):
    status: str = Field(pattern=r"^(requested|acknowledged|in_progress|completed|cancelled)$")


class AuditEvent(BaseModel):
    event_id: int
    actor: str
    action: str
    resource: str
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: str


class VoiceCommand(BaseModel):
    user_id: str
    role: UserRole
    transcript: str = Field(min_length=1)
    locale: str = Field(default="ar-SA", pattern=r"^(ar|en|fr|es)(-[A-Z]{2})?$")
    facility_id: str | None = None
    threshold: int | None = Field(default=None, ge=1)


class VoiceCommandResult(BaseModel):
    intent: str
    response: str
    action: dict[str, Any] | None = None
