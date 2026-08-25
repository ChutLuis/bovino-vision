"""Validate the ArUco scale against a known-height reference (e.g. a person).

Detects the ArUco marker (-> px/cm), detects the person with YOLO (class 0),
measures their pixel height, converts to cm, and compares to the real height.

    python3 src/validate_scale.py --image data/test/foto.jpg --real-height-cm 173 --marker-size-cm 15
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.aruco import ArucoDetector
from core.calibration import from_marker
from ultralytics import YOLO


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--image", required=True)
    p.add_argument("--real-height-cm", type=float, required=True)
    p.add_argument("--marker-size-cm", type=float, default=15.0)
    p.add_argument("--model", default="models/yolo26n.pt")
    p.add_argument("--person-class", type=int, default=0)
    p.add_argument("--out", default="")
    args = p.parse_args()

    frame = cv2.imread(args.image)
    if frame is None:
        raise SystemExit(f"cannot read {args.image}")
    H, W = frame.shape[:2]
    print(f"image: {W}x{H}")

    # 1) marker -> scale
    aruco = ArucoDetector(dictionary_name="DICT_6X6_250", allowed_ids=None, min_marker_size_px=20)
    markers = aruco.detect(frame)
    if not markers:
        raise SystemExit("NO marker detected — try closer / better light / check print.")
    m = max(markers, key=lambda d: d.side_length_px)
    calib = from_marker(m.side_length_px, args.marker_size_cm)
    print(f"marker: id={m.marker_id}  side={m.side_length_px:.1f}px  -> {calib.px_per_cm:.3f} px/cm")

    # 2) person -> pixel height
    model = YOLO(args.model)
    res = model.predict(source=frame, classes=[args.person_class], conf=0.25, verbose=False)
    boxes = res[0].boxes if res else None
    if boxes is None or len(boxes) == 0:
        raise SystemExit("NO person detected.")
    best = max(boxes, key=lambda b: float(b.conf[0]))
    x1, y1, x2, y2 = best.xyxy[0].cpu().numpy().astype(int)
    h_px = y2 - y1
    est_cm = calib.px_to_cm(h_px)
    err = (est_cm - args.real_height_cm) / args.real_height_cm * 100.0

    print(f"person: conf={float(best.conf[0]):.2f}  height={h_px}px")
    print(f"\nESTIMATED HEIGHT: {est_cm:.1f} cm   (real: {args.real_height_cm:.0f} cm)")
    print(f"ERROR: {err:+.1f}%   -> {'OK (scale good)' if abs(err) < 8 else 'check depth-plane alignment'}")

    out = args.out or str(Path(args.image).with_name(Path(args.image).stem + "_check.jpg"))
    ann = ArucoDetector.draw(frame, [m])
    cv2.rectangle(ann, (x1, y1), (x2, y2), (255, 128, 0), 2)
    cv2.putText(ann, f"{est_cm:.0f}cm (real {args.real_height_cm:.0f})", (x1, max(0, y1 - 10)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 128, 0), 2)
    cv2.imwrite(out, ann)
    print(f"overlay -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
