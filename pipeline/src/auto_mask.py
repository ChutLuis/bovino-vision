"""Auto-segment EVERY photo; finalize the clean ones, flag the messy ones for manual.

Per photo (la vaca dominante con YOLO26-seg):
  - guarda la mascara en mascaras/  (SIEMPRE -> etiqueta de entrenamiento)
  - detecta el marcador ArUco (escala)
  - clasifica:
      LISTA        : 1 vaca clara, no cortada, con marcador, area plausible
                     -> mide + overlay en listas/ + fila en medidas.csv (source=auto)
      REVISAR      : varias vacas / oclusion / cortada (con marcador) -> overlay en revisar/  (la dibujas a mano)
      SIN_MARCADOR : sin marcador -> overlay en sin_marcador/  (mascara sirve para entrenar; no medible)

Integra con draw_mask: las LISTAS quedan en listas/ y se saltan; las de revisar/ las completas a mano.

    python3 src/auto_mask.py --dir data/field/raw/_grouped/6700 --cow-id 6700
    python3 src/auto_mask.py --all          # todas las carpetas con peso
"""
from __future__ import annotations
import argparse, csv, re, sys
from collections import defaultdict
from pathlib import Path
import cv2, numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from core.aruco import ArucoDetector
from core.calibration import from_marker
from core.segmenter import CowSegmenter
from core.morphometry import measure

FIELDS = ["photo", "cow_id", "source", "status", "marker_px", "body_length_cm",
          "height_cm", "chest_depth_cm", "lateral_area_cm2", "aspect_ratio", "fill_ratio"]


def overlay(full, mask, label, color):
    ov = full.copy(); col = np.zeros_like(ov); col[mask.astype(bool)] = color
    ov = cv2.addWeighted(ov, 1.0, col, 0.4, 0)
    cv2.putText(ov, label, (30, 70), cv2.FONT_HERSHEY_SIMPLEX, 2.0, color, 4)
    return ov


def process(d: Path, cow_id: str, aruco, seg, marker_cm=15.0):
    masks, listas, revisar, sinmk = d / "mascaras", d / "listas", d / "revisar", d / "sin_marcador"
    for x in (masks, listas, revisar, sinmk):
        x.mkdir(exist_ok=True)
    csvp = d / "medidas.csv"
    existing = {}
    if csvp.exists():
        for r in csv.DictReader(open(csvp)):
            existing[r["photo"]] = r
    done = {q.stem for q in listas.glob("*.jpg")}  # ya finalizadas (auto-lista o manual)

    imgs = sorted(p for p in d.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png"))
    nl = nr = nn = 0
    for p in imgs:
        if p.stem in done:
            continue
        full = cv2.imread(str(p))
        if full is None:
            continue
        H, W = full.shape[:2]
        cows = seg.segment(full)
        if not cows:
            continue
        dom = max(cows, key=lambda c: c.area_px)
        cv2.imwrite(str(masks / f"{p.stem}.png"), dom.mask * 255)  # mascara SIEMPRE

        mks = aruco.detect(full)
        tot = sum(c.area_px for c in cows); domfrac = dom.area_px / tot if tot else 0
        imgfrac = dom.area_px / (H * W)
        x1, y1, x2, y2 = dom.bbox_xyxy; mx, my = 0.015 * W, 0.015 * H
        edge = x1 <= mx or y1 <= my or x2 >= W - mx or y2 >= H - my

        if not mks:
            cv2.imwrite(str(sinmk / f"{p.stem}.jpg"), overlay(full, dom.mask, "SIN MARCADOR", (0, 165, 255))); nn += 1
            continue
        m = max(mks, key=lambda dd: dd.side_length_px)
        clean = dom.confidence >= 0.85 and domfrac >= 0.85 and not edge and 0.03 <= imgfrac <= 0.5
        if clean:
            mo = measure(dom.mask, from_marker(m.side_length_px, marker_cm))
            row = {"photo": p.name, "cow_id": cow_id, "source": "auto", "status": "lista",
                   "marker_px": round(m.side_length_px)}
            row.update(mo.as_features()); existing[p.name] = row
            cv2.imwrite(str(listas / f"{p.stem}.jpg"), overlay(full, dom.mask, "LISTA (auto)", (0, 255, 0))); nl += 1
        else:
            cv2.imwrite(str(revisar / f"{p.stem}.jpg"), overlay(full, dom.mask, "REVISAR", (0, 0, 255))); nr += 1

    if existing:
        with open(csvp, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader()
            for r in existing.values():
                w.writerow({k: r.get(k, "") for k in FIELDS})
    print(f"  {d.name}: {nl} listas(auto), {nr} a revisar, {nn} sin marcador")
    return nl, nr, nn


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir")
    ap.add_argument("--cow-id", default="")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--marker-size-cm", type=float, default=15.0)
    a = ap.parse_args()

    aruco = ArucoDetector("DICT_6X6_250", allowed_ids=None, min_marker_size_px=18)
    seg = CowSegmenter("models/yolo26n-seg.pt", cow_class_id=19, min_confidence=0.45)

    if a.all:
        field = Path("data/field"); grouped = field / "raw" / "_grouped"
        master = list(csv.DictReader(open(field / "master_logbook.csv")))
        fold = defaultdict(list)
        for dd in grouped.iterdir():
            if dd.is_dir() and not dd.name.startswith("_"):
                mm = re.match(r"(\d+)", dd.name)
                if mm:
                    fold[mm.group(1)].append(dd)
        tot = [0, 0, 0]
        for r in master:
            if r["tiene_fotos"] != "si":
                continue
            for dd in fold.get(r["arete"], []):
                nl, nr, nn = process(dd, r["arete"], aruco, seg, a.marker_size_cm)
                tot = [tot[0] + nl, tot[1] + nr, tot[2] + nn]
        print(f"\nTOTAL: {tot[0]} listas auto | {tot[1]} a revisar a mano | {tot[2]} sin marcador")
    else:
        if not a.dir:
            ap.error("usa --dir <carpeta> o --all")
        d = Path(a.dir)
        cid = a.cow_id or re.match(r"(\d+)", d.name).group(1)
        process(d, cid, aruco, seg, a.marker_size_cm)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
