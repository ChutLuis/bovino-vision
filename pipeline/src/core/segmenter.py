"""Cow instance segmentation with YOLO26-seg.

Unlike core.cow_detector (bounding boxes only), this returns per-cow binary
masks — required for morphometry (silhouette area, body length, height, chest
depth). The mask is the cow's projected lateral silhouette.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
from ultralytics import YOLO
from ultralytics.utils import ops


@dataclass
class CowSegmentation:
    confidence: float
    bbox_xyxy: tuple[int, int, int, int]
    mask: np.ndarray  # uint8 binary mask (0/1), same H×W as the input frame

    @property
    def area_px(self) -> int:
        return int(self.mask.sum())


class CowSegmenter:
    def __init__(
        self,
        model_path: str = "yolo26n-seg.pt",
        cow_class_id: int = 19,
        min_confidence: float = 0.5,
        device: str = "",
    ) -> None:
        self._model = YOLO(model_path)
        self._cow_class_id = cow_class_id
        self._min_conf = min_confidence
        self._device = device or None

    def segment(self, frame_bgr: np.ndarray) -> list[CowSegmentation]:
        h, w = frame_bgr.shape[:2]
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
        if r.masks is None or r.boxes is None or len(r.boxes) == 0:
            return []

        out: list[CowSegmentation] = []
        # r.masks.data está a la resolución de ENTRADA de la red (letterbox con relleno, p. ej. 384×640
        # para una foto 16:9), no a la de la imagen. Hay que recortar el relleno antes de escalar:
        # redimensionar directo aplasta la silueta (−6 % de alto en ráfagas 4096×2304). scale_masks
        # hace el recorte y el escalado con la misma geometría que usa Ultralytics para las cajas.
        masks_data = ops.scale_masks(r.masks.data[None].float(), (h, w))[0].cpu().numpy()  # (N, h, w)
        for i, box in enumerate(r.boxes):
            xyxy = box.xyxy[0].cpu().numpy().astype(int)
            conf = float(box.conf[0].cpu().numpy())
            mask = (masks_data[i] > 0.5).astype(np.uint8)
            out.append(
                CowSegmentation(
                    confidence=conf,
                    bbox_xyxy=(int(xyxy[0]), int(xyxy[1]), int(xyxy[2]), int(xyxy[3])),
                    mask=mask,
                )
            )
        return out

    @staticmethod
    def largest(segmentations: list[CowSegmentation]) -> CowSegmentation | None:
        """Return the segmentation with the biggest mask — the cow closest to the
        camera / most fully in frame. Useful when stray cows appear in the back."""
        if not segmentations:
            return None
        return max(segmentations, key=lambda s: s.area_px)

    @staticmethod
    def overlay(frame_bgr: np.ndarray, seg: CowSegmentation, color=(0, 200, 255)) -> np.ndarray:
        out = frame_bgr.copy()
        colored = np.zeros_like(out)
        colored[seg.mask.astype(bool)] = color
        return cv2.addWeighted(out, 1.0, colored, 0.4, 0)
