"""Live debug viewer — overlays ArUco markers and YOLO26 cow detections on webcam feed.

Use this to:
  - Verify the camera is reachable.
  - Validate that printed markers are detected at the expected distances.
  - Sanity-check YOLO26 cow detection (point camera at a phone showing a cow image,
    or run on a recorded cow video via --video).

Press 'q' to quit, 's' to save the current annotated frame to /tmp.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.aruco import ArucoDetector
from core.config import Config
from core.cow_detector import CowDetector


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Live ArUco + YOLO26 cow detector")
    p.add_argument("--config", default="config.yaml")
    p.add_argument("--camera", type=int, default=None, help="Override camera index")
    p.add_argument("--video", default=None, help="Use video file instead of camera")
    p.add_argument("--no-yolo", action="store_true", help="Skip YOLO detection (test ArUco only)")
    return p.parse_args()


def open_source(args: argparse.Namespace, cfg: Config) -> cv2.VideoCapture:
    if args.video:
        cap = cv2.VideoCapture(args.video)
    else:
        cam_index = args.camera if args.camera is not None else cfg.camera.index
        cap = cv2.VideoCapture(cam_index)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, cfg.camera.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cfg.camera.height)
        cap.set(cv2.CAP_PROP_FPS, cfg.camera.fps)
    if not cap.isOpened():
        raise RuntimeError("Could not open video source")
    return cap


def main() -> int:
    args = parse_args()
    cfg = Config.load(args.config) if Path(args.config).exists() else Config()

    aruco = ArucoDetector(
        dictionary_name=cfg.aruco.dictionary,
        allowed_ids=cfg.aruco.marker_ids or None,
        min_marker_size_px=cfg.aruco.min_marker_size_px,
    )
    cow = None
    if not args.no_yolo:
        print(f"Loading YOLO model: {cfg.cow_detector.model} (first run downloads weights)")
        cow = CowDetector(
            model_path=cfg.cow_detector.model,
            cow_class_id=cfg.cow_detector.cow_class_id,
            min_confidence=cfg.cow_detector.min_confidence,
            device=cfg.cow_detector.device,
        )

    cap = open_source(args, cfg)
    print("Press 'q' to quit, 's' to save current frame.")

    last_t = time.monotonic()
    fps_smooth = 0.0
    while True:
        ok, frame = cap.read()
        if not ok:
            print("End of stream.")
            break

        markers = aruco.detect(frame)
        cows = cow.detect(frame) if cow else []

        annotated = frame
        if cows:
            annotated = CowDetector.draw(annotated, cows)
        annotated = ArucoDetector.draw(annotated, markers)

        now = time.monotonic()
        dt = now - last_t
        last_t = now
        if dt > 0:
            fps_smooth = 0.9 * fps_smooth + 0.1 * (1.0 / dt)

        hud = f"FPS {fps_smooth:5.1f}  |  cows {len(cows)}  |  markers {len(markers)}"
        cv2.putText(annotated, hud, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        cv2.imshow("ArUco + YOLO26 cow detector  (q=quit, s=save)", annotated)
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        if key == ord("s"):
            ts = time.strftime("%Y%m%dT%H%M%S")
            out = f"/tmp/detect_live_{ts}.jpg"
            cv2.imwrite(out, annotated)
            print(f"Saved {out}")

    cap.release()
    cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
