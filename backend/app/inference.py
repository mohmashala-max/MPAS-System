from dataclasses import dataclass
from typing import Protocol

from .models import Detection


class YoloV9Detector(Protocol):
    def detect(self, image_uri: str) -> list[Detection]: ...

    @property
    def version(self) -> str: ...


class Sam2Segmenter(Protocol):
    def segment(self, image_uri: str, detections: list[Detection]) -> list[Detection]: ...

    @property
    def version(self) -> str: ...


@dataclass
class MpasVisionPipeline:
    """Production adapter boundary for YOLOv9 detection followed by SAM2 segmentation."""

    detector: YoloV9Detector
    segmenter: Sam2Segmenter

    def analyze(self, image_uri: str) -> tuple[list[Detection], str]:
        detections = self.detector.detect(image_uri)
        segmented = self.segmenter.segment(image_uri, detections)
        return segmented, f"{self.detector.version}+{self.segmenter.version}"
