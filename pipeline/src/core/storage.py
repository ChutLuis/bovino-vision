from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import cv2
import numpy as np


@dataclass
class BurstMetadata:
    marker_id: int
    burst_id: str
    started_at_iso: str
    cow_confidence: float | None
    cow_bbox_xyxy: tuple[int, int, int, int] | None
    marker_bbox_xyxy: tuple[int, int, int, int]
    marker_side_px: float
    frames: list[str] = field(default_factory=list)


class CaptureStorage:
    def __init__(self, root: str | Path, jpeg_quality: int = 92) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._jpeg_params = [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality]

    def burst_dir(self, marker_id: int) -> Path:
        d = self.root / f"aruco_{marker_id:04d}"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def new_burst_id(self) -> str:
        return datetime.now().strftime("%Y%m%dT%H%M%S_%f")[:-3]

    def save_frame(self, marker_id: int, burst_id: str, frame_idx: int, image_bgr: np.ndarray) -> Path:
        d = self.burst_dir(marker_id)
        path = d / f"{burst_id}_f{frame_idx:02d}.jpg"
        cv2.imwrite(str(path), image_bgr, self._jpeg_params)
        return path

    def save_preview(self, marker_id: int, burst_id: str, annotated_bgr: np.ndarray) -> Path:
        d = self.burst_dir(marker_id) / "_previews"
        d.mkdir(parents=True, exist_ok=True)
        path = d / f"{burst_id}.jpg"
        cv2.imwrite(str(path), annotated_bgr, self._jpeg_params)
        return path

    def save_metadata(self, meta: BurstMetadata) -> Path:
        d = self.burst_dir(meta.marker_id)
        path = d / f"{meta.burst_id}.json"
        with open(path, "w") as f:
            json.dump(_serializable(asdict(meta)), f, indent=2, ensure_ascii=False)
        return path


def _serializable(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serializable(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    return obj
