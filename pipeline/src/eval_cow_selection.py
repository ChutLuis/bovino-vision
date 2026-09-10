"""Regla de selección de la vaca objetivo cuando hay varias en el cuadro (RF-07). Solo análisis en PC.

Hoy el APK (segment.ts) y eval_finetuned_iou.py eligen la detección de MAYOR ÁREA; en burst_nahomi_01/02
eso escoge la vaca de adelante y no la lateral junto al marcador. Sobre las 40 imágenes anotadas a mano de
data/val_clean (inst0 = la vaca pesada) se comparan reglas, con la ruta del APK reproducida en PC
(LiteRTCowSegmenter, conf 0.5 = CONFIDENCE_THRESHOLD) y el marcador ArUco (DICT_6X6_250):

  area           mayor área (regla actual del APK)
  marcador_dist  caja más cercana al centro del marcador (distancia 0 si lo contiene); empate -> mayor área
  centro_x       centroide horizontal de la máscara más cercano al marcador
  franja_k       mayor área entre las detecciones cuya caja solapa la franja vertical del marcador ensanchada
                 k lados de marcador a cada lado (k = 0, 1, 2); si ninguna solapa -> area
Sin marcador detectado, todas las reglas caen en 'area'.

Salida: <out>/por_imagen.csv, resumen.md, resumen.json y (con --visual) img/<qid>.jpg de las fotos con
más de una detección.

    python3 src/eval_cow_selection.py --visual
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from core.aruco import ArucoDetector  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TFLITE = ROOT.parent / "app" / "assets" / "model_bundle" / "yolo26n-seg.tflite"
KS = (0, 1, 2)
RULES = ["area", "marcador_dist", "centro_x"] + [f"franja_{k}" for k in KS]


def load_gts(masks_dir: Path, qid: str, w: int, h: int) -> list[np.ndarray]:
    files = sorted(masks_dir.glob(f"{qid}_inst*.png"), key=lambda p: int(re.search(r"_inst(\d+)$", p.stem).group(1)))
    out = []
    for f in files:
        m = cv2.imread(str(f), cv2.IMREAD_GRAYSCALE)
        if m.shape != (h, w):
            m = cv2.resize(m, (w, h), interpolation=cv2.INTER_NEAREST)
        out.append(m > 127)
    return out


def iou(a: np.ndarray, b: np.ndarray) -> float:
    u = np.logical_or(a, b).sum()
    return float(np.logical_and(a, b).sum() / u) if u else 0.0


def bbox_dist(bbox, pt) -> float:
    x1, y1, x2, y2 = bbox; px, py = pt
    dx = max(x1 - px, 0.0, px - x2); dy = max(y1 - py, 0.0, py - y2)
    return float(np.hypot(dx, dy))


def choose(dets, marker) -> dict[str, int]:
    """Índice elegido por cada regla. dets: objetos con .mask, .area_px, .bbox_xyxy."""
    areas = [d.area_px for d in dets]
    by_area = int(np.argmax(areas))
    sel = {r: by_area for r in RULES}
    if marker is None or len(dets) < 2:
        return sel
    mx, my = marker.center
    side = float(marker.side_length_px)
    sel["marcador_dist"] = min(range(len(dets)), key=lambda i: (bbox_dist(dets[i].bbox_xyxy, (mx, my)), -areas[i]))
    cxs = [float(np.nonzero(d.mask)[1].mean()) if d.area_px else 1e9 for d in dets]
    sel["centro_x"] = min(range(len(dets)), key=lambda i: (abs(cxs[i] - mx), -areas[i]))
    xs = marker.corners[:, 0]
    for k in KS:
        lo, hi = float(xs.min()) - k * side, float(xs.max()) + k * side
        cands = [i for i, d in enumerate(dets) if d.bbox_xyxy[0] <= hi and d.bbox_xyxy[2] >= lo]
        sel[f"franja_{k}"] = max(cands, key=lambda i: areas[i]) if cands else by_area
    return sel


def draw(img, gt0, marker, dets, sel):
    vis = img.copy()
    cnts, _ = cv2.findContours(gt0.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(vis, cnts, -1, (0, 255, 255), 6)
    if marker is not None:
        x1, y1, x2, y2 = marker.bbox_xyxy
        cv2.rectangle(vis, (x1, y1), (x2, y2), (255, 255, 0), 6)
    chosen_by = {}
    for r, i in sel.items():
        chosen_by.setdefault(i, []).append(r)
    for i, d in enumerate(dets):
        x1, y1, x2, y2 = d.bbox_xyxy
        rules = chosen_by.get(i, [])
        ok = iou(d.mask, gt0) >= 0.5
        color = (0, 200, 0) if ok else (0, 0, 255)
        cv2.rectangle(vis, (x1, y1), (x2, y2), color, 4 if rules else 2)
        label = f"#{i} a={d.area_px // 1000}k c={d.confidence:.2f}" + (" <- " + ",".join(rules) if rules else "")
        cv2.putText(vis, label, (x1 + 8, max(y1 - 12, 40)), cv2.FONT_HERSHEY_SIMPLEX, 1.4, color, 4)
    h, w = vis.shape[:2]
    s = 1280 / w
    return cv2.resize(vis, (1280, int(h * s)), interpolation=cv2.INTER_AREA)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--val-dir", default=str(ROOT / "data" / "val_clean"))
    ap.add_argument("--tflite", default=str(DEFAULT_TFLITE))
    ap.add_argument("--conf", type=float, default=0.5, help="umbral del APK (CONFIDENCE_THRESHOLD)")
    ap.add_argument("--out", default=str(ROOT.parent / "informes" / f"seleccion_vaca_{date.today().strftime('%Y%m%d')}"))
    ap.add_argument("--visual", action="store_true")
    a = ap.parse_args()

    from core.segmenter_litert import LiteRTCowSegmenter
    seg = LiteRTCowSegmenter(a.tflite, cow_class_id=19, min_confidence=a.conf)
    aruco = ArucoDetector("DICT_6X6_250", allowed_ids=None, min_marker_size_px=18)
    val, out = Path(a.val_dir), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    if a.visual:
        (out / "img").mkdir(exist_ok=True)

    rows = []
    for r in csv.DictReader(open(val / "manifest.csv")):
        qid = r["qid"]
        ip = next((val / "images").glob(f"{qid}.*"), None)
        img = cv2.imread(str(ip))
        h, w = img.shape[:2]
        gts = load_gts(val / "masks", qid, w, h)
        dets = seg.segment(img)
        mks = aruco.detect(img)
        marker = None
        if mks:
            marker = next((m for m in mks if m.marker_id == 0), None) or max(mks, key=lambda m: m.side_length_px)
        row = {"qid": qid, "stratum": r["stratum"], "cow_id": r["cow_id"], "n_gt": len(gts), "n_det": len(dets),
               "marker": int(marker is not None), "marker_id": marker.marker_id if marker else "",
               "marker_side_px": round(marker.side_length_px) if marker else "",
               "marker_in_gt0_bbox": ""}
        if marker is not None:
            ys, xs = np.nonzero(gts[0])
            row["marker_in_gt0_bbox"] = int(xs.min() <= marker.center[0] <= xs.max())
        sel = choose(dets, marker) if dets else {}
        # oráculo: ¿alguna detección recupera la vaca objetivo? Si no, el fallo es de detección, no de selección.
        ious = [iou(d.mask, gts[0]) for d in dets]
        row["oraculo__iou_max"] = round(max(ious), 4) if ious else 0.0
        row["oraculo__ok"] = int(bool(ious) and max(ious) >= 0.5)
        row["oraculo__sel"] = int(np.argmax(ious)) if ious else ""
        for rule in RULES:
            if not dets:
                row[f"{rule}__sel"] = ""; row[f"{rule}__ok"] = 0; row[f"{rule}__iou"] = 0.0; row[f"{rule}__cambia"] = 0
                continue
            i = sel[rule]
            v = iou(dets[i].mask, gts[0])
            row[f"{rule}__sel"] = i; row[f"{rule}__ok"] = int(v >= 0.5); row[f"{rule}__iou"] = round(v, 4)
            row[f"{rule}__cambia"] = int(i != sel["area"])
        rows.append(row)
        if a.visual and len(dets) > 1:
            cv2.imwrite(str(out / "img" / f"{qid}.jpg"), draw(img, gts[0], marker, dets, sel), [cv2.IMWRITE_JPEG_QUALITY, 82])
        flag = "" if row["area__ok"] else "  <-- area falla"
        print(f"{qid:22} dets={len(dets)} marcador={'id' + str(marker.marker_id) if marker else 'NO'} "
              + " ".join(f"{ru}={'ok' if row[f'{ru}__ok'] else 'X'}" for ru in RULES) + flag, flush=True)

    fields = list(rows[0].keys())
    with open(out / "por_imagen.csv", "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=fields); wr.writeheader(); wr.writerows(rows)

    n = len(rows)
    multi = [r for r in rows if r["n_det"] > 1]
    summary = {"fecha": date.today().isoformat(), "tflite": str(a.tflite), "conf": a.conf, "n_imagenes": n,
               "oraculo_alguna_deteccion_recupera_objetivo": f"{sum(r['oraculo__ok'] for r in rows)}/{n}",
               "objetivo_no_detectado": [r["qid"] for r in rows if not r["oraculo__ok"]],
               "con_marcador": sum(r["marker"] for r in rows), "marcador_id0": sum(1 for r in rows if r["marker_id"] == 0),
               "con_mas_de_una_deteccion": len(multi), "sin_deteccion": sum(1 for r in rows if r["n_det"] == 0),
               "reglas": {}}
    for rule in RULES:
        ok = sum(r[f"{rule}__ok"] for r in rows)
        cambia = [r["qid"] for r in rows if r[f"{rule}__cambia"]]
        mejora = [r["qid"] for r in rows if r[f"{rule}__ok"] and not r["area__ok"]]
        empeora = [r["qid"] for r in rows if not r[f"{rule}__ok"] and r["area__ok"]]
        por_estrato = dict(Counter(r["stratum"] for r in rows if r[f"{rule}__ok"]))
        summary["reglas"][rule] = {"eligio_objetivo": f"{ok}/{n}", "iou_objetivo_medio": round(float(np.mean([r[f"{rule}__iou"] for r in rows])), 4),
                                   "cambia_vs_area": cambia, "mejora_vs_area": mejora, "empeora_vs_area": empeora,
                                   "ok_por_estrato": por_estrato}
    (out / "resumen.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")

    md = [f"# Regla de selección de la vaca objetivo — {summary['fecha']}", "",
          f"Modelo: `{Path(a.tflite).name}` (ruta del APK en PC, conf {a.conf}). Referencia: {n} imágenes manuales de `data/val_clean`, inst0 = vaca pesada.",
          f"Con marcador ArUco detectado: {summary['con_marcador']}/{n} (id 0: {summary['marcador_id0']}). Con más de una detección: {len(multi)}/{n}. Sin detección: {summary['sin_deteccion']}.",
          f"Oráculo (alguna detección con IoU ≥ 0.5 contra la vaca objetivo): {summary['oraculo_alguna_deteccion_recupera_objetivo']}; objetivo NO detectado en: {', '.join(summary['objetivo_no_detectado']) or 'ninguna'}.", "",
          "| regla | eligió objetivo | IoU objetivo medio | cambia vs area | mejora | empeora |", "|---|---|---|---|---|---|"]
    for rule, d in summary["reglas"].items():
        md.append(f"| {rule} | {d['eligio_objetivo']} | {d['iou_objetivo_medio']} | {len(d['cambia_vs_area'])} | {len(d['mejora_vs_area'])} | {len(d['empeora_vs_area'])} |")
    md += ["", "## Fotos que cambian de decisión respecto a `area`", ""]
    for rule, d in summary["reglas"].items():
        if d["cambia_vs_area"]:
            md.append(f"- **{rule}**: {', '.join(d['cambia_vs_area'])}" +
                      (f" — mejora: {', '.join(d['mejora_vs_area'])}" if d["mejora_vs_area"] else "") +
                      (f" — empeora: {', '.join(d['empeora_vs_area'])}" if d["empeora_vs_area"] else ""))
    md += ["", "## Fotos con más de una detección", "", "| qid | estrato | dets | marcador | marcador dentro de la caja de inst0 | oráculo | " + " | ".join(RULES) + " |",
           "|---|---|---|---|---|---|" + "---|" * len(RULES)]
    for r in multi:
        md.append(f"| {r['qid']} | {r['stratum']} | {r['n_det']} | {('id ' + str(r['marker_id'])) if r['marker'] else 'no'} | {r['marker_in_gt0_bbox']} | "
                  f"{'ok' if r['oraculo__ok'] else 'X'} (#{r['oraculo__sel']}, IoU {r['oraculo__iou_max']}) | "
                  + " | ".join(("ok" if r[f"{ru}__ok"] else "X") + f" (#{r[f'{ru}__sel']})" for ru in RULES) + " |")
    (out / "resumen.md").write_text("\n".join(md) + "\n")
    print("\n" + "\n".join(md[:12]))
    print(f"-> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
