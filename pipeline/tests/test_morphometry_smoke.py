"""Smoke test for morphometry + regression — no camera, no field data needed.

Part 1: rasterize an ellipse of known cm dimensions and verify measure() recovers
        length / height / area within rasterization tolerance.
Part 2: synthesize a feature table where weight is a known function of features,
        then verify the regression pipeline runs and recovers low error.

Run from prototype/:
    python3 tests/test_morphometry_smoke.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from core.calibration import from_fixed, from_marker
from core.morphometry import measure, barymetric_weight_kg


def test_ellipse_measurements() -> None:
    import cv2

    px_per_cm = 10.0
    calib = from_fixed(px_per_cm)

    # Ellipse: semi-axes a=100cm (length/2), b=60cm (height/2) -> 200x120 cm
    a_cm, b_cm = 100.0, 60.0
    a_px, b_px = int(a_cm * px_per_cm), int(b_cm * px_per_cm)
    H, W = 2 * b_px + 100, 2 * a_px + 100
    mask = np.zeros((H, W), dtype=np.uint8)
    cv2.ellipse(mask, (W // 2, H // 2), (a_px, b_px), 0, 0, 360, 1, thickness=-1)

    morph = measure(mask, calib)
    print(f"  length={morph.body_length_cm}cm (expect ~200)  height={morph.height_cm}cm (expect ~120)")
    print(f"  area={morph.lateral_area_cm2}cm2 (expect ~{round(np.pi * a_cm * b_cm)})")
    print(f"  chest_depth={morph.chest_depth_cm}cm (ellipse: ~height={morph.height_cm})")

    assert abs(morph.body_length_cm - 200.0) < 2.0, morph.body_length_cm
    assert abs(morph.height_cm - 120.0) < 2.0, morph.height_cm
    expected_area = np.pi * a_cm * b_cm
    assert abs(morph.lateral_area_cm2 - expected_area) / expected_area < 0.02, morph.lateral_area_cm2
    # For a filled ellipse, max contiguous vertical run at center == full height
    assert abs(morph.chest_depth_cm - morph.height_cm) < 2.0, morph.chest_depth_cm
    print("  ellipse measurements OK")


def test_marker_calibration() -> None:
    # A 15cm marker spanning 150px -> 10 px/cm
    calib = from_marker(marker_side_px=150.0, marker_size_cm=15.0)
    assert abs(calib.px_per_cm - 10.0) < 1e-9
    assert abs(calib.px_to_cm(200.0) - 20.0) < 1e-9
    assert abs(calib.area_px_to_cm2(10000.0) - 100.0) < 1e-9
    print("  marker calibration OK")


def test_barymetric() -> None:
    # Sanity: a ~165cm girth, 150cm length Jersey -> a few hundred kg
    w = barymetric_weight_kg(thoracic_perimeter_cm=165.0, body_length_cm=150.0)
    print(f"  barymetric(PT=165, LC=150) = {w:.1f} kg")
    assert 300 < w < 450, w
    print("  barymetric formula OK")


def test_regression_pipeline() -> None:
    import pandas as pd
    sys.path.insert(0, str(ROOT / "src"))
    import train_weight_model as twm

    rng = np.random.RandomState(0)
    rows = []
    n_cows = 30
    for cow in range(n_cows):
        # Each cow has a "true size"; weight is a smooth function of it + noise
        size = rng.uniform(0.8, 1.4)
        length = 180 * size + rng.normal(0, 2)
        height = 130 * size + rng.normal(0, 2)
        depth = 70 * size + rng.normal(0, 1.5)
        area = 1.1 * length * height / 1.0 + rng.normal(0, 200)
        true_weight = 0.0009 * area + 1.5 * depth + rng.normal(0, 6)
        for _ in range(4):  # 4 photos per cow
            rows.append({
                "cow_id": f"cow_{cow:02d}",
                "weight_kg": true_weight + rng.normal(0, 3),
                "body_length_cm": length + rng.normal(0, 1),
                "height_cm": height + rng.normal(0, 1),
                "chest_depth_cm": depth + rng.normal(0, 0.8),
                "lateral_area_cm2": area + rng.normal(0, 80),
                "aspect_ratio": length / height,
                "fill_ratio": rng.uniform(0.6, 0.75),
            })
    df = pd.DataFrame(rows)

    with tempfile.TemporaryDirectory() as td:
        csv = Path(td) / "features.csv"
        df.to_csv(csv, index=False)
        out = Path(td) / "model.joblib"
        rc = twm.main(["--csv", str(csv), "--out", str(out), "--model", "linear"])
        assert rc == 0
        assert out.exists()
    print("  regression pipeline OK")


def main() -> int:
    print("Part 1 — marker calibration:")
    test_marker_calibration()
    print("Part 2 — ellipse morphometry:")
    test_ellipse_measurements()
    print("Part 3 — barymetric baseline:")
    test_barymetric()
    print("Part 4 — regression pipeline (synthetic 30 cows):")
    test_regression_pipeline()
    print("\nOK — morphometry + regression smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
