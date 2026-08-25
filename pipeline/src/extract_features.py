"""Bridge: field photos + field logbook -> feature table ready for training.

For each labeled photo: detect the ArUco scale marker -> px/cm, segment the cow
with YOLO26-seg -> silhouette, measure morphometry -> cm features, then join with
the ground-truth weight/measurements from your logbook CSV.

Logbook CSV (one row per PHOTO) — minimum columns:
    photo        filename (relative to --images-dir)
    cow_id       ear-tag / animal id
    weight_kg    cinta bovinométrica or scale weight
  Optional (for validation / barymetric baseline):
    thoracic_perimeter_cm, body_length_cm_tape, height_cm_tape

Output CSV adds the CV-extracted features and is consumed directly by
train_weight_model.py.

Example:
    python3 src/extract_features.py \
        --images-dir data/field/photos \
        --labels data/field/logbook.csv \
        --marker-size-cm 15 \
        --out data/field/features.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.aruco import ArucoDetector
from core.calibration import from_fixed, from_marker
from core.config import Config
from core.morphometry import measure
from core.segmenter import CowSegmenter


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Extract morphometry features from labeled field photos")
    p.add_argument("--images-dir", required=True)
    p.add_argument("--labels", required=True, help="Logbook CSV (one row per photo)")
    p.add_argument("--out", default="data/field/features.csv")
    p.add_argument("--config", default="config.yaml")
    p.add_argument("--marker-size-cm", type=float, default=15.0)
    p.add_argument("--seg-model", default="yolo26n-seg.pt")
    p.add_argument("--fixed-px-per-cm", type=float, default=0.0,
                   help="Fallback scale if no marker is found (from a fixed-camera calibration)")
    p.add_argument("--save-overlays", action="store_true",
                   help="Write annotated mask+marker previews next to the output for QA")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    import pandas as pd

    cfg = Config.load(args.config) if Path(args.config).exists() else Config()
    images_dir = Path(args.images_dir)
    labels = pd.read_csv(args.labels)
    for req in ("photo", "cow_id", "weight_kg"):
        if req not in labels.columns:
            raise SystemExit(f"labels CSV missing required column: {req}")

    aruco = ArucoDetector(
        dictionary_name=cfg.aruco.dictionary,
        allowed_ids=cfg.aruco.marker_ids or None,
        min_marker_size_px=cfg.aruco.min_marker_size_px,
    )
    segmenter = CowSegmenter(
        model_path=args.seg_model,
        cow_class_id=cfg.cow_detector.cow_class_id,
        min_confidence=cfg.cow_detector.min_confidence,
        device=cfg.cow_detector.device,
    )

    overlay_dir = Path(args.out).with_suffix("")
    if args.save_overlays:
        overlay_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    skipped = []
    for _, lab in labels.iterrows():
        photo_path = images_dir / str(lab["photo"])
        frame = cv2.imread(str(photo_path))
        if frame is None:
            skipped.append((lab["photo"], "image not found / unreadable"))
            continue

        # 1) scale
        markers = aruco.detect(frame)
        if markers:
            biggest = max(markers, key=lambda m: m.side_length_px)
            calib = from_marker(biggest.side_length_px, args.marker_size_cm)
            scale_source = f"marker_id{biggest.marker_id}"
        elif args.fixed_px_per_cm > 0:
            calib = from_fixed(args.fixed_px_per_cm)
            scale_source = "fixed"
        else:
            skipped.append((lab["photo"], "no marker found and no --fixed-px-per-cm"))
            continue

        # 2) segment cow -> biggest silhouette
        segs = segmenter.segment(frame)
        seg = CowSegmenter.largest(segs)
        if seg is None:
            skipped.append((lab["photo"], "no cow segmented"))
            continue

        # 3) measure
        morph = measure(seg.mask, calib)

        row = dict(lab)
        row.update(morph.as_features())
        row["scale_source"] = scale_source
        row["cow_confidence"] = round(seg.confidence, 3)
        rows.append(row)

        if args.save_overlays:
            ov = CowSegmenter.overlay(frame, seg)
            ov = ArucoDetector.draw(ov, markers)
            cv2.imwrite(str(overlay_dir / f"{Path(str(lab['photo'])).stem}_qa.jpg"), ov)

    if not rows:
        raise SystemExit("No features extracted — check images, marker, and labels CSV.")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(out, index=False)

    print(f"Extracted features for {len(rows)} photos -> {out}")
    print(f"Cows represented: {df['cow_id'].nunique()}")
    if skipped:
        print(f"\nSkipped {len(skipped)} photos:")
        for name, why in skipped[:20]:
            print(f"  {name}: {why}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
