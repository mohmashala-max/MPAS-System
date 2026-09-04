from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from .models import Detection, InspectionResult


class ObjectStorage(Protocol):
    def signed_url(self, object_uri: str, expires_seconds: int = 900) -> str: ...


class InferenceProvider(Protocol):
    def detect(self, image_uri: str) -> list[Detection]: ...

    def segment(self, image_uri: str, detections: list[Detection]) -> list[Detection]: ...

    @property
    def model_version(self) -> str: ...


class ErpClient(Protocol):
    def create_work_order(self, event: "WorkOrderRequested") -> str: ...

    def update_work_order(self, external_id: str, status: str) -> None: ...


class NotificationProvider(Protocol):
    def notify(self, facility_id: str, event: "WorkOrderRequested") -> None: ...


@dataclass(frozen=True)
class WorkOrderRequested:
    event_id: str
    facility_id: str
    trap_id: str
    pest_count: int
    threshold: int
    priority: str
    occurred_at: datetime

    @classmethod
    def from_inspection(cls, result: InspectionResult, threshold: int, model_version: str) -> "WorkOrderRequested":
        if not result.work_order:
            raise ValueError("An inspection without a work order cannot create an ERP event")
        event_id = f"{result.facility_id}:{result.trap_id}:{model_version}:{result.pest_count}"
        return cls(
            event_id=event_id,
            facility_id=result.facility_id,
            trap_id=result.trap_id,
            pest_count=result.pest_count,
            threshold=threshold,
            priority=str(result.work_order["priority"]),
            occurred_at=datetime.now(timezone.utc),
        )


class IdempotentWorkOrderPublisher:
    """Publishes each event once; replace the set with a durable event store in production."""

    def __init__(self, erp: ErpClient, notifications: NotificationProvider):
        self.erp = erp
        self.notifications = notifications
        self.published: dict[str, str] = {}

    def publish(self, event: WorkOrderRequested) -> str:
        if event.event_id in self.published:
            return self.published[event.event_id]
        external_id = self.erp.create_work_order(event)
        self.published[event.event_id] = external_id
        self.notifications.notify(event.facility_id, event)
        return external_id
