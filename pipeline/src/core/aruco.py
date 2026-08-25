from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

_DICTIONARIES = {
    name: getattr(cv2.aruco, name)
    for name in dir(cv2.aruco)
    if name.startswith("DICT_")
}


@dataclass
class ArucoDetection:
    marker_id: int
    corners: np.ndarray  # shape (4, 2), float32, in pixel coords
    center: tuple[float, float]
    side_length_px: float

    @property
    def bbox_xyxy(self) -> tuple[int, int, int, int]:
        xs, ys = self.corners[:, 0], self.corners[:, 1]
        return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


class ArucoDetector:
    def __init__(
        self,
        dictionary_name: str = "DICT_6X6_250",
        allowed_ids: list[int] | None = None,
        min_marker_size_px: int = 60,
    ) -> None:
        if dictionary_name not in _DICTIONARIES:
            raise ValueError(f"Unknown ArUco dictionary: {dictionary_name}")
        self._dict = cv2.aruco.getPredefinedDictionary(_DICTIONARIES[dictionary_name])
        self._params = cv2.aruco.DetectorParameters()
        self._detector = cv2.aruco.ArucoDetector(self._dict, self._params)
        self._allowed_ids = set(allowed_ids) if allowed_ids else None
        self._min_size_px = min_marker_size_px

    def detect(self, frame_bgr: np.ndarray) -> list[ArucoDetection]:
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        corners, ids, _ = self._detector.detectMarkers(gray)
        if ids is None or len(ids) == 0:
            return []

        out: list[ArucoDetection] = []
        for marker_corners, marker_id in zip(corners, ids.flatten()):
            mid = int(marker_id)
            if self._allowed_ids is not None and mid not in self._allowed_ids:
                continue
            pts = marker_corners.reshape(4, 2).astype(np.float32)
            side = float(np.linalg.norm(pts[0] - pts[1]))
            if side < self._min_size_px:
                continue
            cx, cy = pts.mean(axis=0)
            out.append(
                ArucoDetection(
                    marker_id=mid,
                    corners=pts,
                    center=(float(cx), float(cy)),
                    side_length_px=side,
                )
            )
        return out

    @staticmethod
    def draw(frame_bgr: np.ndarray, detections: list[ArucoDetection]) -> np.ndarray:
        out = frame_bgr.copy()
        for d in detections:
            pts = d.corners.astype(np.int32).reshape(-1, 1, 2)
            cv2.polylines(out, [pts], isClosed=True, color=(0, 255, 0), thickness=2)
            x, y = int(d.center[0]), int(d.center[1])
            cv2.putText(
                out,
                f"ID {d.marker_id}",
                (x - 30, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2,
            )
        return out
