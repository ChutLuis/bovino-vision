from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class CameraConfig:
    index: int = 0
    width: int = 1280
    height: int = 720
    fps: int = 30


@dataclass
class ArucoConfig:
    dictionary: str = "DICT_6X6_250"
    marker_ids: list[int] = field(default_factory=lambda: list(range(50)))
    physical_size_cm: float = 15.0
    min_marker_size_px: int = 60


@dataclass
class CowDetectorConfig:
    model: str = "yolo26n.pt"
    cow_class_id: int = 19
    min_confidence: float = 0.50
    device: str = ""


@dataclass
class TriggerConfig:
    burst_count: int = 5
    burst_interval_ms: int = 400
    cooldown_seconds: int = 30
    require_cow_overlap: bool = True
    require_lateral_pose: bool = False


@dataclass
class StorageConfig:
    root: str = "data/captures"
    jpeg_quality: int = 92
    save_annotated_preview: bool = True


@dataclass
class LoggingConfig:
    level: str = "INFO"
    file: str = "prototype.log"


@dataclass
class Config:
    camera: CameraConfig = field(default_factory=CameraConfig)
    aruco: ArucoConfig = field(default_factory=ArucoConfig)
    cow_detector: CowDetectorConfig = field(default_factory=CowDetectorConfig)
    trigger: TriggerConfig = field(default_factory=TriggerConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    @classmethod
    def load(cls, path: str | Path) -> Config:
        with open(path) as f:
            raw: dict[str, Any] = yaml.safe_load(f) or {}
        return cls(
            camera=CameraConfig(**raw.get("camera", {})),
            aruco=ArucoConfig(**{k: v for k, v in raw.get("aruco", {}).items() if k != "min_decode_confidence"}),
            cow_detector=CowDetectorConfig(**raw.get("cow_detector", {})),
            trigger=TriggerConfig(**raw.get("trigger", {})),
            storage=StorageConfig(**raw.get("storage", {})),
            logging=LoggingConfig(**raw.get("logging", {})),
        )
