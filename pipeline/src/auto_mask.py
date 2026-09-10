"""Segmenta TODAS las fotos de las ráfagas con el segmentador de PC y escribe las máscaras en
un directorio de salida propio (nunca encima de los crudos).

Por foto (la vaca dominante = mayor área, misma regla que el APK):
  - guarda la máscara en <out>/<carpeta>/mascaras/<stem>.png  (SIEMPRE -> etiqueta de entrenamiento)
  - detecta el marcador ArUco (escala)
  - clasifica y lo anota en <out>/triage.csv:
      lista        : 1 vaca clara, no cortada, con marcador, área plausible -> fila en medidas.csv (source=auto)
      revisar      : varias vacas / oclusión / cortada (con marcador)
      sin_marcador : sin marcador (la máscara sirve para entrenar; no medible)
      sin_vaca     : el segmentador no devolvió ninguna vaca
  - con --overlays además escribe los JPEG de control en listas/, revisar/ y sin_marcador/.

Ruta de los crudos, en orden: --raw, $BOVINO_RAW_GROUPED, data/field/raw/_grouped,
~/Documents/Thesis_final_raw/raw/_grouped (misma regla que build_yolo_seg_dataset.py).

Historial: hasta el 9 sep 2026 este script escribía en <carpeta>/mascaras/ dentro de los crudos y
leía data/field/master_logbook.csv; esos PNG (respaldo en mascaras_backup.zip) se generaron con el
recorte del relleno del letterbox sin corregir (máscaras 16:9 aplastadas un 6 % en vertical).

    python3 src/auto_mask.py --all --out data/field/rafagas_mascaras_20260909
    python3 src/auto_mask.py --dir 6700 --out /tmp/prueba --overlays
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import time
from datetime import date
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_yolo_seg_dataset import resolve_grouped  # noqa: E402
from core.aruco import ArucoDetector  # noqa: E402
from core.calibration import from_marker  # noqa: E402
from core.morphometry import measure  # noqa: E402
from core.segmenter import CowSegmenter  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL = ROOT / "models" / "yolo26n-seg.pt"

FIELDS = ["photo", "cow_id", "source", "status", "marker_px", "body_length_cm",
          "height_cm", "chest_depth_cm", "lateral_area_cm2", "aspect_ratio", "fill_ratio"]
TRIAGE = ["folder", "photo", "status", "n_cows", "dom_conf", "dom_frac", "img_frac", "edge", "marker_px",
          "mask_h_px", "mask_w_px", "area_px"]


def overlay(full, mask, label, color):
    ov = full.copy(); col = np.zeros_like(ov); col[mask.astype(bool)] = color
    ov = cv2.addWeighted(ov, 1.0, col, 0.4, 0)
    cv2.putText(ov, label, (30, 70), cv2.FONT_HERSHEY_SIMPLEX, 2.0, color, 4)
    return ov


def sha256_16(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def process(d: Path, cow_id: str, aruco, seg, out_root: Path, marker_cm=15.0, overlays=False, done: set | None = None):
    """Segmenta las fotos de la carpeta d y escribe en out_root/d.name. Devuelve las filas de triage.

    done: pares (carpeta, foto) que ya tienen fila en triage.csv; solo esas se saltan al reanudar
    (una máscara escrita sin fila de triage se vuelve a segmentar: la salida es determinista)."""
    out = out_root / d.name
    masks = out / "mascaras"
    masks.mkdir(parents=True, exist_ok=True)
    listas, revisar, sinmk = out / "listas", out / "revisar", out / "sin_marcador"
    if overlays:
        for x in (listas, revisar, sinmk):
            x.mkdir(exist_ok=True)
    csvp = out / "medidas.csv"
    existing = {}
    if csvp.exists():
        for r in csv.DictReader(open(csvp)):
            existing[r["photo"]] = r

    imgs = sorted(p for p in d.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png"))
    rows = []
    n = {"lista": 0, "revisar": 0, "sin_marcador": 0, "sin_vaca": 0, "reanudada": 0}
    for p in imgs:
        if done and (d.name, p.name) in done:  # reanudar una corrida interrumpida
            n["reanudada"] += 1
            continue
        full = cv2.imread(str(p))
        if full is None:
            continue
        H, W = full.shape[:2]
        cows = seg.segment(full)
        tri = {"folder": d.name, "photo": p.name, "n_cows": len(cows)}
        if not cows:
            tri["status"] = "sin_vaca"; n["sin_vaca"] += 1; rows.append(tri)
            continue
        dom = max(cows, key=lambda c: c.area_px)
        cv2.imwrite(str(masks / f"{p.stem}.png"), dom.mask * 255)  # máscara SIEMPRE

        ys, xs = np.nonzero(dom.mask)
        tot = sum(c.area_px for c in cows); domfrac = dom.area_px / tot if tot else 0
        imgfrac = dom.area_px / (H * W)
        x1, y1, x2, y2 = dom.bbox_xyxy; mx, my = 0.015 * W, 0.015 * H
        edge = x1 <= mx or y1 <= my or x2 >= W - mx or y2 >= H - my
        tri.update({"dom_conf": round(dom.confidence, 3), "dom_frac": round(domfrac, 3), "img_frac": round(imgfrac, 4),
                    "edge": int(edge), "area_px": int(dom.area_px),
                    "mask_h_px": int(ys.max() - ys.min() + 1) if len(ys) else 0,
                    "mask_w_px": int(xs.max() - xs.min() + 1) if len(xs) else 0})

        mks = aruco.detect(full)
        if not mks:
            tri["status"] = "sin_marcador"; n["sin_marcador"] += 1; rows.append(tri)
            if overlays:
                cv2.imwrite(str(sinmk / f"{p.stem}.jpg"), overlay(full, dom.mask, "SIN MARCADOR", (0, 165, 255)))
            continue
        m = max(mks, key=lambda dd: dd.side_length_px)
        tri["marker_px"] = round(m.side_length_px)
        clean = dom.confidence >= 0.85 and domfrac >= 0.85 and not edge and 0.03 <= imgfrac <= 0.5
        if clean:
            mo = measure(dom.mask, from_marker(m.side_length_px, marker_cm))
            row = {"photo": p.name, "cow_id": cow_id, "source": "auto", "status": "lista",
                   "marker_px": round(m.side_length_px)}
            row.update(mo.as_features()); existing[p.name] = row
            tri["status"] = "lista"; n["lista"] += 1
            if overlays:
                cv2.imwrite(str(listas / f"{p.stem}.jpg"), overlay(full, dom.mask, "LISTA (auto)", (0, 255, 0)))
        else:
            tri["status"] = "revisar"; n["revisar"] += 1
            if overlays:
                cv2.imwrite(str(revisar / f"{p.stem}.jpg"), overlay(full, dom.mask, "REVISAR", (0, 0, 255)))
        rows.append(tri)

    if existing:
        with open(csvp, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader()
            for r in existing.values():
                w.writerow({k: r.get(k, "") for k in FIELDS})
    print(f"  {d.name}: {len(imgs)} fotos | {n['lista']} listas(auto), {n['revisar']} a revisar, "
          f"{n['sin_marcador']} sin marcador, {n['sin_vaca']} sin vaca, {n['reanudada']} ya hechas", flush=True)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw", help="directorio _grouped con las ráfagas (ver orden de búsqueda arriba)")
    ap.add_argument("--dir", help="una sola carpeta: nombre dentro de _grouped (p. ej. 6700) o ruta")
    ap.add_argument("--cow-id", default="", help="identificador para medidas.csv; por defecto los dígitos de la carpeta")
    ap.add_argument("--all", action="store_true", help="todas las carpetas <dígitos>* de _grouped")
    ap.add_argument("--out", required=True, help="directorio de salida (se crea; nunca se escribe en --raw)")
    ap.add_argument("--overlays", action="store_true", help="escribir JPEG de control (listas/, revisar/, sin_marcador/)")
    ap.add_argument("--model", default=str(DEFAULT_MODEL))
    ap.add_argument("--conf", type=float, default=0.45)
    ap.add_argument("--marker-size-cm", type=float, default=15.0)
    a = ap.parse_args()

    grouped = resolve_grouped(a.raw)
    out_root = Path(a.out).expanduser().resolve()
    if out_root == grouped.resolve() or grouped.resolve() in out_root.parents:
        raise SystemExit(f"--out no puede estar dentro de los crudos ({grouped})")
    out_root.mkdir(parents=True, exist_ok=True)

    model = Path(a.model)
    if not model.exists():
        raise SystemExit(f"no existe el modelo {model}")
    aruco = ArucoDetector("DICT_6X6_250", allowed_ids=None, min_marker_size_px=18)
    seg = CowSegmenter(str(model), cow_class_id=19, min_confidence=a.conf)

    if a.all:
        dirs = sorted(dd for dd in grouped.iterdir() if dd.is_dir() and re.match(r"\d+", dd.name))
    elif a.dir:
        d = Path(a.dir)
        dirs = [d if d.is_dir() else grouped / a.dir]
        if not dirs[0].is_dir():
            raise SystemExit(f"no existe la carpeta {dirs[0]}")
    else:
        ap.error("usa --dir <carpeta> o --all")

    import ultralytics
    info = {"fecha": date.today().isoformat(), "raw": str(grouped), "out": str(out_root), "modelo": str(model),
            "modelo_sha256_16": sha256_16(model), "conf": a.conf, "cow_class_id": 19,
            "ultralytics": ultralytics.__version__, "carpetas": [d.name for d in dirs],
            "nota": "máscaras de la vaca de mayor área con CowSegmenter (recorte del relleno del letterbox corregido, commit 0fd6669)"}
    (out_root / "run_info.json").write_text(json.dumps(info, indent=2, ensure_ascii=False) + "\n")

    tri = out_root / "triage.csv"
    old = [r for r in csv.DictReader(open(tri))] if tri.exists() else []
    done = {(r["folder"], r["photo"]) for r in old}

    t0 = time.time()
    all_rows = []
    for dd in dirs:
        cid = a.cow_id or re.match(r"(\d+)", dd.name).group(1)
        all_rows += process(dd, cid, aruco, seg, out_root, a.marker_size_cm, a.overlays, done)

    new = {(r["folder"], r["photo"]) for r in all_rows}
    merged = [r for r in old if (r["folder"], r["photo"]) not in new] + all_rows
    with open(tri, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=TRIAGE); w.writeheader()
        for r in sorted(merged, key=lambda r: (r["folder"], r["photo"])):
            w.writerow({k: r.get(k, "") for k in TRIAGE})
    from collections import Counter
    c = Counter(r["status"] for r in merged)
    print(f"\nTOTAL {len(merged)} fotos: " + ", ".join(f"{k}={v}" for k, v in sorted(c.items()))
          + f" | {time.time() - t0:.0f} s | máscaras en {out_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
