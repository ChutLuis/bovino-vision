from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
from ultralytics import YOLO


@dataclass
class CowDetection:
    confidence: float
    bbox_xyxy: tuple[int, int, int, int]

    @property
    def area(self) -> int:
        x1, y1, x2, y2 = self.bbox_xyxy
        return max(0, x2 - x1) * max(0, y2 - y1)

    def contains_point(self, x: float, y: float) -> bool:
        x1, y1, x2, y2 = self.bbox_xyxy
        return x1 <= x <= x2 and y1 <= y <= y2

    def iou(self, other_xyxy: tuple[int, int, int, int]) -> float:
        ax1, ay1, ax2, ay2 = self.bbox_xyxy
        bx1, by1, bx2, by2 = other_xyxy
        ix1, iy1 = max(ax1, bx1), max(ay1, by1)
        ix2, iy2 = min(ax2, bx2), min(ay2, by2)
        iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
        inter = iw * ih
        if inter == 0:
            return 0.0
        a_area = (ax2 - ax1) * (ay2 - ay1)
        b_area = (bx2 - bx1) * (by2 - by1)
        return inter / (a_area + b_area - inter)


class CowDetector:
    def __init__(
        self,
        model_path: str = "yolo26n.pt",
        cow_class_id: int = 19,
        min_confidence: float = 0.5,
        device: str = "",
    ) -> None:
        self._model = YOLO(model_path)
        self._cow_class_id = cow_class_id
        self._min_conf = min_confidence
        self._device = device or None

    def detect(self, frame_bgr: np.ndarray) -> list[CowDetection]:
        results = self._model.predict(
            source=frame_bgr,
            classes=[self._cow_class_id],
            conf=self._min_conf,
            verbose=False,
            device=self._device,
        )
        if not results:
            return []
        r = results[0]
        if r.boxes is None or len(r.boxes) == 0:
            return []
        out: list[CowDetection] = []
        for box in r.boxes:
            xyxy = box.xyxy[0].cpu().numpy().astype(int)
            conf = float(box.conf[0].cpu().numpy())
            out.append(
                CowDetection(
                    confidence=conf,
                    bbox_xyxy=(int(xyxy[0]), int(xyxy[1]), int(xyxy[2]), int(xyxy[3])),
                )
            )
        return out

    @staticmethod
    def draw(frame_bgr: np.ndarray, detections: list[CowDetection]) -> np.ndarray:
        out = frame_bgr.copy()
        for d in detections:
            x1, y1, x2, y2 = d.bbox_xyxy
            cv2.rectangle(out, (x1, y1), (x2, y2), (255, 128, 0), 2)
            cv2.putText(
                out,
                f"cow {d.confidence:.2f}",
                (x1, max(0, y1 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 128, 0),
                2,
            )
        return out
