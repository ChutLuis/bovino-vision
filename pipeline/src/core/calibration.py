"""Scale calibration — convert pixels to centimeters.

Two modes:
  1. Marker-based: an ArUco marker of known physical size is in the frame.
     px_per_cm = marker_side_px / marker_size_cm.
  2. Fixed-camera: the camera is mounted at a fixed distance from the cow's
     passing plane. You calibrate once (place a known-size object at that plane,
     measure its pixel size) and store px_per_cm in config. No per-frame marker
     needed — but a marker is still recommended as a per-frame sanity check.

For the thesis field setup (fixed C270 at a common passing point), mode 2 is the
primary path and mode 1 validates it frame by frame.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ScaleCalibration:
    px_per_cm: float
    source: str  # "marker" | "fixed"

    def px_to_cm(self, length_px: float) -> float:
        return length_px / self.px_per_cm

    def cm_to_px(self, length_cm: float) -> float:
        return length_cm * self.px_per_cm

    def area_px_to_cm2(self, area_px: float) -> float:
        return area_px / (self.px_per_cm ** 2)


def from_marker(marker_side_px: float, marker_size_cm: float) -> ScaleCalibration:
    """Build a calibration from a detected ArUco marker.

    marker_side_px: average side length of the marker in pixels (we have this as
                    ArucoDetection.side_length_px).
    marker_size_cm: the physical side length of the printed marker (e.g. 15.0).
    """
    if marker_side_px <= 0 or marker_size_cm <= 0:
        raise ValueError("marker_side_px and marker_size_cm must be positive")
    return ScaleCalibration(px_per_cm=marker_side_px / marker_size_cm, source="marker")


def from_fixed(px_per_cm: float) -> ScaleCalibration:
    """Build a calibration from a pre-measured fixed-camera value."""
    if px_per_cm <= 0:
        raise ValueError("px_per_cm must be positive")
    return ScaleCalibration(px_per_cm=px_per_cm, source="fixed")


def calibrate_fixed_from_reference(reference_px: float, reference_cm: float) -> ScaleCalibration:
    """One-time fixed-camera calibration helper.

    Place an object of known length (reference_cm) at the cow's passing plane,
    measure how many pixels it spans (reference_px), and this returns the
    px_per_cm to store in config.yaml under camera.px_per_cm.
    """
    if reference_px <= 0 or reference_cm <= 0:
        raise ValueError("reference_px and reference_cm must be positive")
    return ScaleCalibration(px_per_cm=reference_px / reference_cm, source="fixed")
