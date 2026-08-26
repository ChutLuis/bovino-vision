"""Prueba de paridad de escala ArUco: backend móvil (js-aruco2) vs OpenCV subpíxel.

Compara las esquinas reportadas por el APK de benchmark (benchmark_results.json)
contra cv2.aruco con refinamiento subpíxel sobre las mismas fotos. La escala
cm/px entra al área al cuadrado y de ahí al peso: un sesgo sistemático de escala
se convierte en sesgo de peso en todos los animales.

Criterio de paridad (docs/03_arquitectura_apk.md): diferencia de escala ≤ 1%.

Uso:
    .venv/bin/python src/eval_aruco_parity.py \
        --json ~/Downloads/benchmark_results.json \
        --photos ../app-benchmark/assets/photos
"""
import argparse
import glob
import json
import os

import cv2
import numpy as np


def side_px(corners):
    c = np.array(corners, dtype=float)
    return float(np.mean([np.linalg.norm(c[i] - c[(i + 1) % 4]) for i in range(4)]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", required=True, help="benchmark_results.json exportado del APK")
    ap.add_argument("--photos", required=True, help="directorio con las mismas fotos del benchmark")
    ap.add_argument("--marker-id", type=int, default=0)
    args = ap.parse_args()

    res = json.load(open(os.path.expanduser(args.json)))
    device_corners = {f"photo_{a['foto']}.jpeg": a for a in res["aruco"] if a.get("decoded")}

    params = cv2.aruco.DetectorParameters()
    params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
    detector = cv2.aruco.ArucoDetector(
        cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_250), params
    )

    diffs_scale, diffs_area = [], []
    print(f"{'foto':<24} {'lado_movil':>10} {'lado_cv':>8} {'dif_escala%':>11} {'dif_area%':>9}")
    for path in sorted(glob.glob(os.path.join(args.photos, "photo_*.jpeg"))):
        name = os.path.basename(path)
        if name not in device_corners:
            continue
        corners, ids, _ = detector.detectMarkers(cv2.imread(path))
        if ids is None or args.marker_id not in ids.flatten():
            print(f"{name:<24} OpenCV NO detectó ID {args.marker_id}")
            continue
        i = list(ids.flatten()).index(args.marker_id)
        cv_side = side_px(corners[i][0])
        mv = device_corners[name]
        mv_side = side_px([[c["x"], c["y"]] for c in mv["corners"]])
        d_scale = (15 / mv_side - 15 / cv_side) / (15 / cv_side) * 100
        d_area = ((15 / mv_side) ** 2 - (15 / cv_side) ** 2) / (15 / cv_side) ** 2 * 100
        diffs_scale.append(d_scale)
        diffs_area.append(d_area)
        print(f"{name:<24} {mv_side:10.2f} {cv_side:8.2f} {d_scale:+10.2f}% {d_area:+8.2f}%")

    if not diffs_scale:
        print("Sin pares comparables.")
        return
    same_sign = all(d > 0 for d in diffs_scale) or all(d < 0 for d in diffs_scale)
    print(f"\nEscala cm/px: dif media {np.mean(diffs_scale):+.2f}% | |max| {np.max(np.abs(diffs_scale)):.2f}%")
    print(f"Área cm²   : dif media {np.mean(diffs_area):+.2f}% | |max| {np.max(np.abs(diffs_area)):.2f}%")
    print(f"Sesgo sistemático (mismo signo en todas): {same_sign}")
    veredicto = "PASA" if np.max(np.abs(diffs_scale)) <= 1.0 else "FALLA"
    print(f"Criterio ≤1% de escala: {veredicto}")


if __name__ == "__main__":
    main()
