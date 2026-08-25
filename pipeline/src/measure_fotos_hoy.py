"""Mide morfometria de las 35 fotos_hoy (1 vaca por foto) y une con el peso.

Reusa el MISMO core que el resto del pipeline: ArucoDetector -> escala (marcador 15cm),
CowSegmenter (YOLO26-seg, vaca dominante), morphometry.measure -> features en cm.

Entrada:  data/field/mapeo_fotos_hoy.csv  (orden, foto, nombre, arete, peso_lb, peso_kg)
Salida:
  data/field/features_fotos_hoy.csv   (cow_id=nombre, weight_kg, features...) -> train_weight_model
  data/field/fotos_hoy/mascaras/*.png  (mascara por foto; editable a mano si hace falta)
  data/field/fotos_hoy/qa/*.jpg        (overlay silueta+marcador para revision visual)
  clasifica cada foto: lista / revisar (oclusion, corte, dominancia) / sin_marcador / escala_dudosa

    python3 src/measure_fotos_hoy.py
"""
from __future__ import annotations
import csv, sys
from pathlib import Path
import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from core.aruco import ArucoDetector
from core.calibration import from_marker
from core.segmenter import CowSegmenter
from core.morphometry import measure

MARKER_CM = 15.0
# rango plausible de longitud corporal (cm) para Jersey adulta de perfil; fuera -> escala sospechosa
PLAUS_LEN = (110.0, 190.0)

OUT_FIELDS = ["orden", "photo", "cow_id", "arete", "weight_kg", "weight_lb", "status",
              "marker_px", "px_per_cm", "cow_conf", "dom_frac",
              "body_length_cm", "height_cm", "chest_depth_cm",
              "lateral_area_cm2", "aspect_ratio", "fill_ratio"]


def main() -> int:
    field = Path("data/field")
    rows_map = list(csv.DictReader(open(field / "mapeo_fotos_hoy.csv")))

    out_dir = field / "fotos_hoy"
    masks_dir, qa_dir = out_dir / "mascaras", out_dir / "qa"
    for d in (masks_dir, qa_dir):
        d.mkdir(parents=True, exist_ok=True)

    aruco = ArucoDetector("DICT_6X6_250", allowed_ids=None, min_marker_size_px=18)
    seg = CowSegmenter("models/yolo26n-seg.pt", cow_class_id=19, min_confidence=0.45)

    out_rows, counts = [], {"lista": 0, "revisar": 0, "sin_marcador": 0, "escala_dudosa": 0, "sin_vaca": 0}
    print(f"{'#':>2} {'nombre':16} {'peso_kg':>7} {'len_cm':>7} {'alt_cm':>7} {'mk_px':>6} {'status'}")
    print("-" * 72)
    for r in rows_map:
        if not r["foto"]:
            continue
        photo = field / r["foto"]
        full = cv2.imread(str(photo))
        nombre = r["nombre"]
        base = {"orden": r["orden"], "photo": r["foto"], "cow_id": nombre, "arete": r["arete"],
                "weight_kg": r["peso_kg"], "weight_lb": r["peso_lb"]}
        if full is None:
            print(f"{r['orden']:>2} {nombre:16} {'':>7} {'':>7} {'':>7} {'':>6} sin_imagen")
            continue
        H, W = full.shape[:2]
        cows = seg.segment(full)
        if not cows:
            counts["sin_vaca"] += 1
            out_rows.append({**base, "status": "sin_vaca"})
            print(f"{r['orden']:>2} {nombre:16} {float(r['peso_kg']):>7.1f} {'':>7} {'':>7} {'':>6} sin_vaca")
            continue
        dom = max(cows, key=lambda c: c.area_px)
        tot = sum(c.area_px for c in cows)
        dom_frac = dom.area_px / tot if tot else 0.0
        cv2.imwrite(str(masks_dir / f"{photo.stem}.png"), dom.mask * 255)

        mks = aruco.detect(full)
        # QA overlay
        ov = CowSegmenter.overlay(full, dom)
        ov = ArucoDetector.draw(ov, mks)

        if not mks:
            counts["sin_marcador"] += 1
            cv2.putText(ov, f"#{r['orden']} {nombre} SIN MARCADOR", (30, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0, 165, 255), 3)
            cv2.imwrite(str(qa_dir / f"{r['orden']}_{nombre}.jpg"), ov)
            out_rows.append({**base, "status": "sin_marcador", "cow_conf": round(dom.confidence, 3),
                             "dom_frac": round(dom_frac, 3)})
            print(f"{r['orden']:>2} {nombre:16} {float(r['peso_kg']):>7.1f} {'':>7} {'':>7} {'':>6} sin_marcador")
            continue

        m = max(mks, key=lambda dd: dd.side_length_px)
        calib = from_marker(m.side_length_px, MARKER_CM)
        mo = measure(dom.mask, calib)

        # clasificacion (mismas ideas que auto_mask + chequeo de escala)
        x1, y1, x2, y2 = dom.bbox_xyxy
        mx, my = 0.015 * W, 0.015 * H
        edge = x1 <= mx or y1 <= my or x2 >= W - mx or y2 >= H - my
        imgfrac = dom.area_px / (H * W)
        clean = dom.confidence >= 0.85 and dom_frac >= 0.85 and not edge and 0.03 <= imgfrac <= 0.5
        if not (PLAUS_LEN[0] <= mo.body_length_cm <= PLAUS_LEN[1]):
            status = "escala_dudosa"
        elif clean:
            status = "lista"
        else:
            status = "revisar"
        counts[status] += 1

        cv2.putText(ov, f"#{r['orden']} {nombre} {status} len={mo.body_length_cm:.0f}cm",
                    (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.2,
                    (0, 200, 0) if status == "lista" else (0, 0, 255), 3)
        cv2.imwrite(str(qa_dir / f"{r['orden']}_{nombre}.jpg"), ov)

        row = {**base, "status": status, "marker_px": round(m.side_length_px),
               "px_per_cm": round(calib.px_per_cm, 4), "cow_conf": round(dom.confidence, 3),
               "dom_frac": round(dom_frac, 3)}
        row.update(mo.as_features())
        out_rows.append(row)
        print(f"{r['orden']:>2} {nombre:16} {float(r['peso_kg']):>7.1f} "
              f"{mo.body_length_cm:>7.1f} {mo.height_cm:>7.1f} {round(m.side_length_px):>6} {status}")

    out_csv = field / "features_fotos_hoy.csv"
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=OUT_FIELDS)
        w.writeheader()
        for r in out_rows:
            w.writerow({k: r.get(k, "") for k in OUT_FIELDS})

    medible = [r for r in out_rows if r.get("status") in ("lista", "revisar")]
    print("\nresumen:", {k: v for k, v in counts.items() if v})
    print(f"medibles (lista+revisar): {len(medible)} / {len(out_rows)}")
    print(f"-> {out_csv}")
    print(f"-> overlays QA en {qa_dir}  (revisa las 'revisar' / 'escala_dudosa' / 'sin_marcador')")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
