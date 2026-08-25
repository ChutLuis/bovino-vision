"""End-to-end smoke test for the capture pipeline.

Builds a synthetic frame (cow photo + ArUco marker composited over it), feeds
it to the detectors, and exercises the trigger + storage code path.
Run from prototype/:
    python3 tests/test_pipeline_smoke.py
"""

from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from core.aruco import ArucoDetector, _DICTIONARIES
from core.config import Config
from core.cow_detector import CowDetector
from core.storage import BurstMetadata, CaptureStorage
from core.trigger import CooldownTracker


def build_synthetic_frame(cow_jpg: Path, marker_id: int, dict_name: str) -> np.ndarray:
    frame = cv2.imread(str(cow_jpg))
    assert frame is not None, f"could not read {cow_jpg}"

    aruco_dict = cv2.aruco.getPredefinedDictionary(_DICTIONARIES[dict_name])
    marker = cv2.aruco.generateImageMarker(aruco_dict, marker_id, 180)
    marker_bgr = cv2.cvtColor(marker, cv2.COLOR_GRAY2BGR)

    # Pad with white quiet zone (mimics PVC border on collar)
    pad = 20
    padded = cv2.copyMakeBorder(marker_bgr, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=(255, 255, 255))
    h, w = padded.shape[:2]

    # Paste over the bottom-left of the frame (over part of the cow body)
    fh, fw = frame.shape[:2]
    y0 = fh - h - 20
    x0 = 30
    frame[y0:y0 + h, x0:x0 + w] = padded
    return frame


def main() -> int:
    cow_jpg = Path("/tmp/test_cow.jpg")
    if not cow_jpg.exists():
        print("Missing /tmp/test_cow.jpg — run the cow-detection smoke test first")
        return 1

    cfg = Config.load(ROOT / "prototype" / "config.yaml") if (ROOT / "prototype" / "config.yaml").exists() else Config.load(ROOT / "config.yaml")

    # Use a temp output root so the test is self-contained
    out_root = ROOT / "data" / "captures_test"
    if out_root.exists():
        shutil.rmtree(out_root)

    aruco = ArucoDetector(
        dictionary_name=cfg.aruco.dictionary,
        allowed_ids=cfg.aruco.marker_ids,
        min_marker_size_px=cfg.aruco.min_marker_size_px,
    )
    cow_det = CowDetector(
        model_path=str(ROOT / cfg.cow_detector.model),
        cow_class_id=cfg.cow_detector.cow_class_id,
        min_confidence=cfg.cow_detector.min_confidence,
        device=cfg.cow_detector.device,
    )
    storage = CaptureStorage(out_root, jpeg_quality=cfg.storage.jpeg_quality)
    cooldown = CooldownTracker(cooldown_seconds=2.0)  # short for test

    target_id = 3
    frame = build_synthetic_frame(cow_jpg, target_id, cfg.aruco.dictionary)
    cv2.imwrite("/tmp/test_synthetic_frame.jpg", frame)

    markers = aruco.detect(frame)
    cows = cow_det.detect(frame)
    print(f"frame: {frame.shape}  markers={len(markers)}  cows={len(cows)}")
    for m in markers:
        print(f"  marker id={m.marker_id}  side={m.marker_side_px:.0f}px" if False else f"  marker id={m.marker_id}  side={m.side_length_px:.0f}px")
    for c in cows:
        print(f"  cow conf={c.confidence:.2f}  bbox={c.bbox_xyxy}")

    assert any(m.marker_id == target_id for m in markers), "expected marker not detected"
    assert len(cows) > 0, "expected at least one cow detection"

    # Simulate a burst: save 5 frames + metadata
    marker = next(m for m in markers if m.marker_id == target_id)
    cow = max(cows, key=lambda c: c.confidence)
    assert cooldown.can_fire(marker.marker_id)

    burst_id = storage.new_burst_id()
    meta = BurstMetadata(
        marker_id=marker.marker_id,
        burst_id=burst_id,
        started_at_iso="2026-05-21T20:30:00Z",
        cow_confidence=cow.confidence,
        cow_bbox_xyxy=cow.bbox_xyxy,
        marker_bbox_xyxy=marker.bbox_xyxy,
        marker_side_px=marker.side_length_px,
    )
    for i in range(5):
        path = storage.save_frame(marker.marker_id, burst_id, i, frame)
        meta.frames.append(path.name)
    storage.save_metadata(meta)
    cooldown.mark_fired(marker.marker_id)

    # Cooldown blocks immediate refire
    assert not cooldown.can_fire(marker.marker_id), "cooldown should block immediate refire"
    print(f"cooldown blocks refire: time_until_ready={cooldown.time_until_ready(marker.marker_id):.2f}s")
    time.sleep(2.1)
    assert cooldown.can_fire(marker.marker_id), "cooldown should expire"
    print("cooldown expires correctly")

    # Verify files
    burst_dir = out_root / f"aruco_{target_id:04d}"
    files = sorted(p.name for p in burst_dir.iterdir())
    print(f"files in {burst_dir.relative_to(ROOT)}:")
    for f in files:
        print(f"  {f}")
    assert any(f.endswith(".json") for f in files)
    assert sum(1 for f in files if f.endswith(".jpg")) == 5

    print("\nOK — pipeline smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
