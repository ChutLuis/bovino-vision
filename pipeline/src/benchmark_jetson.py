"""Mide FPS del pipeline de inferencia completo (para reportar en §4 / Recomendaciones).

Cronometra por etapa sobre imágenes reales: segmentación YOLO26-seg + detección ArUco +
morfometría + estimación de peso (alométrico). Reporta ms por etapa y FPS de extremo a extremo.
Correr EN LA JETSON (y opcionalmente en la Mac para comparar).

    # en la Jetson:
    python3 src/benchmark_jetson.py --device cuda:0 --n 100
    # en la Mac (comparación):
    python3 src/benchmark_jetson.py --device mps --n 50
    python3 src/benchmark_jetson.py --device cpu --n 30
"""
from __future__ import annotations
import argparse, glob, time, sys
from pathlib import Path
import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from core.aruco import ArucoDetector
from core.calibration import from_marker
from core.segmenter import CowSegmenter
from core.morphometry import measure

# modelo alométrico ajustado (W = a * A^b), área lateral en cm²
ALO_A, ALO_B, MARKER_CM = 0.3745, 0.706, 15.0


def predict_weight(area_cm2: float) -> float:
    return ALO_A * (area_cm2 ** ALO_B) if area_cm2 > 0 else float("nan")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default="", help='"", "cpu", "mps", "cuda:0"')
    ap.add_argument("--n", type=int, default=100, help="iteraciones cronometradas")
    ap.add_argument("--warmup", type=int, default=10)
    ap.add_argument("--seg-model", default="models/yolo26n-seg.pt")
    ap.add_argument("--images", default="data/field/WhatsApp Image 2026-06-05*.jpeg")
    a = ap.parse_args()

    paths = sorted(glob.glob(a.images))[2:]  # salta las 2 hojas de papel
    if not paths:
        raise SystemExit(f"sin imágenes en {a.images}")
    imgs = [cv2.imread(p) for p in paths]
    imgs = [im for im in imgs if im is not None]

    seg = CowSegmenter(a.seg_model, cow_class_id=19, min_confidence=0.45, device=a.device)
    aruco = ArucoDetector("DICT_6X6_250", allowed_ids=None, min_marker_size_px=18)

    def run_once(im):
        t = {}
        t0 = time.perf_counter()
        cows = seg.segment(im); t["seg"] = time.perf_counter() - t0
        t0 = time.perf_counter()
        mks = aruco.detect(im); t["aruco"] = time.perf_counter() - t0
        t0 = time.perf_counter()
        if cows and mks:
            dom = max(cows, key=lambda c: c.area_px)
            m = max(mks, key=lambda d: d.side_length_px)
            mo = measure(dom.mask, from_marker(m.side_length_px, MARKER_CM))
            _ = predict_weight(mo.lateral_area_cm2)
        t["morph+peso"] = time.perf_counter() - t0
        return t

    for i in range(a.warmup):
        run_once(imgs[i % len(imgs)])

    acc = {"seg": 0.0, "aruco": 0.0, "morph+peso": 0.0}
    t_start = time.perf_counter()
    for i in range(a.n):
        for k, v in run_once(imgs[i % len(imgs)]).items():
            acc[k] += v
    total = time.perf_counter() - t_start

    print(f"device={a.device or 'auto'}  n={a.n}  imágenes={len(imgs)}")
    print(f"{'etapa':14} {'ms/frame':>10}")
    for k in ("seg", "aruco", "morph+peso"):
        print(f"{k:14} {acc[k]/a.n*1000:>10.2f}")
    per_frame = total / a.n
    print(f"{'TOTAL':14} {per_frame*1000:>10.2f}")
    print(f"\nFPS extremo a extremo: {1.0/per_frame:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
