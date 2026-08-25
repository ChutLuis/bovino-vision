"""Autonomous capture pipeline.

Streams from the camera, runs YOLO26 + ArUco on every frame, and when both
agree (cow present, marker decoded and large enough, cooldown elapsed), fires
a configurable burst of frames into the per-animal storage folder.

Designed to run unattended on the Jetson Orin Nano in the field.
"""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.aruco import ArucoDetection, ArucoDetector
from core.config import Config
from core.cow_detector import CowDetection, CowDetector
from core.storage import BurstMetadata, CaptureStorage
from core.trigger import CooldownTracker


_stop = False


def _on_signal(*_):  # noqa: ANN001
    global _stop
    _stop = True


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Autonomous cow + ArUco capture pipeline")
    p.add_argument("--config", default="config.yaml")
    p.add_argument("--camera", type=int, default=None, help="Override camera index from config")
    p.add_argument("--video", default=None, help="Process a video file instead of live camera")
    p.add_argument("--show", action="store_true", help="Show live window (debug only — off in production)")
    p.add_argument("--max-bursts", type=int, default=0, help="Stop after N bursts (0 = unlimited)")
    return p.parse_args()


def setup_logging(level: str, file: str) -> logging.Logger:
    log = logging.getLogger("capture")
    log.setLevel(getattr(logging, level.upper(), logging.INFO))
    log.handlers.clear()

    fmt = logging.Formatter("%(asctime)s  %(levelname)-7s  %(message)s")

    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    log.addHandler(sh)

    fh = logging.FileHandler(file)
    fh.setFormatter(fmt)
    log.addHandler(fh)

    return log


def open_source(args: argparse.Namespace, cfg: Config) -> cv2.VideoCapture:
    if args.video:
        cap = cv2.VideoCapture(args.video)
    else:
        idx = args.camera if args.camera is not None else cfg.camera.index
        cap = cv2.VideoCapture(idx)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, cfg.camera.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cfg.camera.height)
        cap.set(cv2.CAP_PROP_FPS, cfg.camera.fps)
    if not cap.isOpened():
        raise RuntimeError("Could not open video source")
    return cap


def best_cow_for_marker(
    marker: ArucoDetection, cows: list[CowDetection]
) -> CowDetection | None:
    if not cows:
        return None
    cx, cy = marker.center
    containing = [c for c in cows if c.contains_point(cx, cy)]
    pool = containing or cows
    return max(pool, key=lambda c: c.confidence)


def fire_burst(
    cap: cv2.VideoCapture,
    storage: CaptureStorage,
    marker: ArucoDetection,
    cow: CowDetection | None,
    cfg: Config,
    log: logging.Logger,
) -> BurstMetadata:
    burst_id = storage.new_burst_id()
    meta = BurstMetadata(
        marker_id=marker.marker_id,
        burst_id=burst_id,
        started_at_iso=datetime.now(timezone.utc).isoformat(),
        cow_confidence=cow.confidence if cow else None,
        cow_bbox_xyxy=cow.bbox_xyxy if cow else None,
        marker_bbox_xyxy=marker.bbox_xyxy,
        marker_side_px=marker.side_length_px,
    )

    interval = cfg.trigger.burst_interval_ms / 1000.0
    saved = 0
    for i in range(cfg.trigger.burst_count):
        if i > 0:
            time.sleep(interval)
        ok, frame = cap.read()
        if not ok:
            log.warning("Burst %s frame %d: camera read failed", burst_id, i)
            continue
        path = storage.save_frame(marker.marker_id, burst_id, i, frame)
        meta.frames.append(path.name)
        saved += 1
    storage.save_metadata(meta)
    log.info(
        "BURST  marker=%d  frames=%d/%d  cow_conf=%s  marker_px=%.0f",
        marker.marker_id,
        saved,
        cfg.trigger.burst_count,
        f"{cow.confidence:.2f}" if cow else "n/a",
        marker.marker_side_px,
    )
    return meta


def main() -> int:
    args = parse_args()
    cfg = Config.load(args.config) if Path(args.config).exists() else Config()

    log = setup_logging(cfg.logging.level, cfg.logging.file)
    log.info("Starting capture pipeline. Config: %s", args.config)

    aruco = ArucoDetector(
        dictionary_name=cfg.aruco.dictionary,
        allowed_ids=cfg.aruco.marker_ids or None,
        min_marker_size_px=cfg.aruco.min_marker_size_px,
    )
    cow_det = CowDetector(
        model_path=cfg.cow_detector.model,
        cow_class_id=cfg.cow_detector.cow_class_id,
        min_confidence=cfg.cow_detector.min_confidence,
        device=cfg.cow_detector.device,
    )
    storage = CaptureStorage(cfg.storage.root, jpeg_quality=cfg.storage.jpeg_quality)
    cooldown = CooldownTracker(cooldown_seconds=cfg.trigger.cooldown_seconds)

    signal.signal(signal.SIGINT, _on_signal)
    signal.signal(signal.SIGTERM, _on_signal)

    cap = open_source(args, cfg)
    burst_count = 0
    frame_count = 0

    try:
        while not _stop:
            ok, frame = cap.read()
            if not ok:
                log.info("End of stream")
                break
            frame_count += 1

            markers = aruco.detect(frame)
            if not markers:
                if args.show:
                    cv2.imshow("capture", frame)
                    if (cv2.waitKey(1) & 0xFF) == ord("q"):
                        break
                continue

            cows = cow_det.detect(frame)

            for marker in markers:
                if not cooldown.can_fire(marker.marker_id):
                    continue
                if cfg.trigger.require_cow_overlap and not cows:
                    continue
                cow = best_cow_for_marker(marker, cows)
                if cfg.trigger.require_cow_overlap and cow is None:
                    continue

                if cfg.storage.save_annotated_preview:
                    annotated = CowDetector.draw(frame, cows)
                    annotated = ArucoDetector.draw(annotated, [marker])
                    burst_preview_id = storage.new_burst_id()
                    storage.save_preview(marker.marker_id, burst_preview_id, annotated)

                fire_burst(cap, storage, marker, cow, cfg, log)
                cooldown.mark_fired(marker.marker_id)
                burst_count += 1

                if args.max_bursts and burst_count >= args.max_bursts:
                    log.info("Reached --max-bursts=%d, stopping", args.max_bursts)
                    return 0

            if args.show:
                annotated = CowDetector.draw(frame, cows)
                annotated = ArucoDetector.draw(annotated, markers)
                cv2.imshow("capture", annotated)
                if (cv2.waitKey(1) & 0xFF) == ord("q"):
                    break
    finally:
        cap.release()
        if args.show:
            cv2.destroyAllWindows()
        log.info("Stopped. frames=%d bursts=%d", frame_count, burst_count)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
