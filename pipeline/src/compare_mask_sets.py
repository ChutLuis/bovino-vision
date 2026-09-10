"""Compara dos juegos de máscaras de ráfagas foto a foto: IoU, área y alto de la silueta.

Uso típico: las máscaras originales de jun 2026 (en los crudos, generadas con el recorte del
letterbox sin corregir) contra la regeneración de auto_mask.py --out.

    python3 src/compare_mask_sets.py --new ~/Documents/Thesis_final_raw/mascaras_regen_20260909 \\
        --out informes/mascaras_rafagas_regen_20260909
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_yolo_seg_dataset import resolve_grouped  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
COLS = ["folder", "photo", "iou", "area_old", "area_new", "area_ratio", "h_old", "h_new", "h_ratio", "w_old", "w_new", "w_ratio"]


def bbox_hw(m: np.ndarray) -> tuple[int, int]:
    ys, xs = np.nonzero(m)
    if not len(ys):
        return 0, 0
    return int(ys.max() - ys.min() + 1), int(xs.max() - xs.min() + 1)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--old", help="raíz con <carpeta>/mascaras/*.png; por defecto los crudos (_grouped)")
    ap.add_argument("--new", required=True, help="raíz con <carpeta>/mascaras/*.png (salida de auto_mask.py --out)")
    ap.add_argument("--out", required=True, help="directorio para comparacion_mascaras.csv y resumen.json")
    a = ap.parse_args()

    old_root = Path(a.old).expanduser() if a.old else resolve_grouped(None)
    new_root = Path(a.new).expanduser()
    out = Path(a.out).expanduser(); out.mkdir(parents=True, exist_ok=True)

    rows, only_old, only_new = [], [], []
    for d in sorted(p for p in old_root.iterdir() if p.is_dir() and not p.name.startswith("_")):
        om = {p.stem: p for p in (d / "mascaras").glob("*.png")} if (d / "mascaras").is_dir() else {}
        nm = {p.stem: p for p in (new_root / d.name / "mascaras").glob("*.png")} if (new_root / d.name / "mascaras").is_dir() else {}
        only_old += [f"{d.name}/{s}" for s in sorted(set(om) - set(nm))]
        only_new += [f"{d.name}/{s}" for s in sorted(set(nm) - set(om))]
        for s in sorted(set(om) & set(nm)):
            mo = cv2.imread(str(om[s]), cv2.IMREAD_GRAYSCALE) > 127
            mn = cv2.imread(str(nm[s]), cv2.IMREAD_GRAYSCALE) > 127
            if mo.shape != mn.shape:
                mn = cv2.resize(mn.astype(np.uint8), (mo.shape[1], mo.shape[0]), interpolation=cv2.INTER_NEAREST) > 0
            inter, union = int((mo & mn).sum()), int((mo | mn).sum())
            ho, wo = bbox_hw(mo); hn, wn = bbox_hw(mn)
            ao, an = int(mo.sum()), int(mn.sum())
            rows.append({"folder": d.name, "photo": s, "iou": round(inter / union, 4) if union else 0.0,
                         "area_old": ao, "area_new": an, "area_ratio": round(an / ao, 4) if ao else "",
                         "h_old": ho, "h_new": hn, "h_ratio": round(hn / ho, 4) if ho else "",
                         "w_old": wo, "w_new": wn, "w_ratio": round(wn / wo, 4) if wo else ""})

    with open(out / "comparacion_mascaras.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS); w.writeheader(); w.writerows(rows)

    iou = np.array([r["iou"] for r in rows], float)
    ar = np.array([r["area_ratio"] for r in rows if r["area_ratio"] != ""], float)
    hr = np.array([r["h_ratio"] for r in rows if r["h_ratio"] != ""], float)
    wr = np.array([r["w_ratio"] for r in rows if r["w_ratio"] != ""], float)
    q = lambda v: {"mediana": round(float(np.median(v)), 4), "p5": round(float(np.percentile(v, 5)), 4),
                   "p95": round(float(np.percentile(v, 95)), 4), "min": round(float(v.min()), 4), "max": round(float(v.max()), 4)}
    res = {"old": str(old_root), "new": str(new_root), "pares": len(rows),
           "solo_en_old": only_old, "solo_en_new": only_new,
           "iou": q(iou), "iou_lt_0.90": int((iou < 0.90).sum()), "iou_lt_0.50": int((iou < 0.50).sum()),
           "area_new/old": q(ar), "alto_new/old": q(hr), "ancho_new/old": q(wr),
           "peores_iou": [f"{r['folder']}/{r['photo']} iou={r['iou']}" for r in sorted(rows, key=lambda r: r["iou"])[:15]]}
    (out / "resumen.json").write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({k: v for k, v in res.items() if k not in ("solo_en_old", "solo_en_new", "peores_iou")}, indent=1, ensure_ascii=False))
    print(f"solo en old: {len(only_old)} | solo en new: {len(only_new)}")
    print("peores IoU:", *res["peores_iou"][:8], sep="\n  ")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
