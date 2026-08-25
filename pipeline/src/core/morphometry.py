"""Morphometry extraction from a lateral cow silhouette mask.

Given a binary mask (the cow's projected side-view silhouette) and a scale
calibration (px → cm), compute physical measurements that predict live weight.

IMPORTANT — assumptions and their limits (state these in Cap 5, Discusión):
  - The camera is a fixed lateral view; the cow is roughly side-on and standing.
  - Measurements are PROJECTED (2D). True heart-girth circumference cannot be
    recovered from a single side view (it needs body width too). We therefore
    measure side-view-observable proxies and let the regression map them to
    weight, validated against tape measurements.
  - body_length_cm  ≈ horizontal extent of the silhouette (nose/shoulder to rump,
                       includes whatever the mask captures).
  - height_cm       ≈ vertical extent (withers/back down to hooves if standing).
  - chest_depth_cm  ≈ max vertical body thickness over the front 60% of the body
                       (a heart-girth-region proxy; legs are excluded by taking the
                       largest *contiguous* vertical run per column).
  - lateral_area_cm2≈ silhouette area — the single most robust weight predictor.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

from .calibration import ScaleCalibration


@dataclass
class Morphometry:
    body_length_cm: float
    height_cm: float
    chest_depth_cm: float
    lateral_area_cm2: float
    aspect_ratio: float        # length / height (dimensionless, scale-invariant)
    fill_ratio: float          # area / bbox_area (silhouette "solidity")
    area_px: int
    px_per_cm: float

    def as_features(self) -> dict[str, float]:
        """Feature dict for the regression model (drops bookkeeping fields)."""
        return {
            "body_length_cm": self.body_length_cm,
            "height_cm": self.height_cm,
            "chest_depth_cm": self.chest_depth_cm,
            "lateral_area_cm2": self.lateral_area_cm2,
            "aspect_ratio": self.aspect_ratio,
            "fill_ratio": self.fill_ratio,
        }

    def to_dict(self) -> dict:
        return asdict(self)


def _largest_contiguous_run(column: np.ndarray) -> int:
    """Length of the longest run of True (1) values in a 1-D boolean array.

    Used per-column to isolate the body thickness from the legs: at a column
    through the chest the body is one tall contiguous run; at a column through
    the legs there are gaps, so the largest run is the belly/body portion."""
    best = run = 0
    for v in column:
        if v:
            run += 1
            if run > best:
                best = run
        else:
            run = 0
    return best


def measure(mask: np.ndarray, calib: ScaleCalibration) -> Morphometry:
    """Extract morphometry from a binary silhouette mask."""
    m = (mask > 0)
    ys, xs = np.where(m)
    if xs.size == 0:
        raise ValueError("empty mask — no cow silhouette to measure")

    x0, x1 = int(xs.min()), int(xs.max())
    y0, y1 = int(ys.min()), int(ys.max())
    width_px = (x1 - x0 + 1)
    height_px = (y1 - y0 + 1)
    area_px = int(m.sum())

    # Chest depth: scan the front 60% of the body width, take the max contiguous
    # vertical run. (We don't know facing direction, so scan both ends and take
    # the deeper region — chest is deeper than the rump/neck for cattle.)
    front_span = max(1, int(0.6 * width_px))
    left_cols = range(x0, x0 + front_span)
    right_cols = range(x1 - front_span + 1, x1 + 1)

    def max_run_over(cols) -> int:
        best = 0
        for cx in cols:
            run = _largest_contiguous_run(m[:, cx])
            if run > best:
                best = run
        return best

    chest_depth_px = max(max_run_over(left_cols), max_run_over(right_cols))

    body_length_cm = calib.px_to_cm(width_px)
    height_cm = calib.px_to_cm(height_px)
    chest_depth_cm = calib.px_to_cm(chest_depth_px)
    lateral_area_cm2 = calib.area_px_to_cm2(area_px)
    aspect_ratio = width_px / height_px if height_px else 0.0
    fill_ratio = area_px / (width_px * height_px) if (width_px * height_px) else 0.0

    return Morphometry(
        body_length_cm=round(body_length_cm, 2),
        height_cm=round(height_cm, 2),
        chest_depth_cm=round(chest_depth_cm, 2),
        lateral_area_cm2=round(lateral_area_cm2, 2),
        aspect_ratio=round(aspect_ratio, 4),
        fill_ratio=round(fill_ratio, 4),
        area_px=area_px,
        px_per_cm=round(calib.px_per_cm, 4),
    )


def barymetric_weight_kg(thoracic_perimeter_cm: float, body_length_cm: float) -> float:
    """Classic Schaeffer-type barymetric estimate (reference baseline only).

    Peso (kg) ≈ (perímetro torácico² × longitud) / 10840.
    Requires the TRUE thoracic perimeter (tape-measured), which a single lateral
    image cannot provide directly. Use this as a baseline to compare against the
    CV-based regression, and as a ground-truth source if you weigh with a
    cinta bovinométrica.
    """
    if thoracic_perimeter_cm <= 0 or body_length_cm <= 0:
        raise ValueError("measurements must be positive")
    return (thoracic_perimeter_cm ** 2 * body_length_cm) / 10840.0
