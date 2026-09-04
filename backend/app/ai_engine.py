from collections.abc import Callable
from typing import Protocol

from .models import Detection, InspectionRequest, InspectionResult, VoiceCommand, VoiceCommandResult


InferenceProvider = Callable[[str], list[Detection]]


class VisionPipeline(Protocol):
    def analyze(self, image_uri: str) -> tuple[list[Detection], str]: ...


class MPASInternalAIEngine:
    """Deterministic orchestration boundary for YOLOv9/SAM2 model adapters.

    Production deployments inject model adapters here; business decisions remain
    testable without GPU weights or external providers.
    """

    def __init__(
        self,
        inference_provider: InferenceProvider | None = None,
        vision_pipeline: VisionPipeline | None = None,
    ):
        self.inference_provider = inference_provider
        self.vision_pipeline = vision_pipeline

    def inspect(self, request: InspectionRequest) -> InspectionResult:
        detections = request.detections
        model_version = None
        if self.vision_pipeline is not None:
            detections, model_version = self.vision_pipeline.analyze(request.image_uri)
        if self.inference_provider is not None:
            detections = self.inference_provider(request.image_uri)
        pest_count = sum(1 for item in detections if item.confidence >= 0.5)
        threshold = request.threshold or 5
        threshold_exceeded = pest_count >= threshold
        work_order = None
        if threshold_exceeded:
            work_order = {
                "type": "pest-treatment",
                "priority": "high" if pest_count >= threshold * 2 else "normal",
                "facility_id": request.facility_id,
                "trap_id": request.trap_id,
                "reason": f"pest count {pest_count} reached threshold {threshold}",
            }
        return InspectionResult(
            facility_id=request.facility_id,
            trap_id=request.trap_id,
            detections=detections,
            pest_count=pest_count,
            threshold_exceeded=threshold_exceeded,
            work_order=work_order,
            model_version=model_version,
        )

    def handle_voice(self, command: VoiceCommand) -> VoiceCommandResult:
        text = command.transcript.casefold()
        if any(token in text for token in ("threshold", "تجاوز", "حد", "alerte", "umbral")):
            threshold = command.threshold or 5
            return VoiceCommandResult(
                intent="create_alert_rule",
                response="تم إعداد تنبيه عند تجاوز عتبة الآفات لهذه المنشأة.",
                action={"type": "alert_rule", "threshold": threshold},
            )
        if any(token in text for token in ("work order", "أمر عمل", "ordre", "orden")):
            return VoiceCommandResult(
                intent="list_work_orders",
                response="جاري تجهيز أوامر العمل المفتوحة.",
                action={"type": "list_work_orders"},
            )
        return VoiceCommandResult(
            intent="unknown",
            response="لم أفهم الأمر. اطلب أوامر العمل أو إعداد تنبيه للعتبة.",
        )
