"""Paridad del segmentador: .pt (pipeline) vs LiteRT emulado en PC (ruta del APK) vs A25 real.

A) Las 10 fotos del benchmark (app-benchmark/assets/photos): la emulación LiteRT en PC debe reproducir
   casi exactamente lo que registró el Galaxy A25 (informes/benchmark_a25_*.json: cow_dets, mask_area_px,
   confianza, caja). Si coincide, lo que se mida en PC con el .tflite vale para el teléfono.
   Además: área LiteRT vs área .pt (criterio de docs/03: diferencia ≤ 1 %).
B) Las 40 imágenes de data/val_clean: .pt vs LiteRT-PC en la máscara elegida (IoU entre ambas, diferencia
   de área) y si ambas eligen la vaca objetivo (inst0).

    python3 src/eval_segmenter_parity.py            # escribe informes/paridad_segmentador_<fecha>/
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from core.seg_eval import iou, load_gt_pngs  # noqa: E402
from core.segmenter_litert import LiteRTCowSegmenter  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def largest(segs):
    return max(segs, key=lambda s: s.area_px) if segs else None


def pct(a, b):
    return (a - b) / b * 100 if b else float("nan")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pt", default=str(ROOT / "models/yolo26n-seg.pt"))
    ap.add_argument("--tflite", default=str(ROOT.parent / "app/assets/model_bundle/yolo26n-seg.tflite"))
    ap.add_argument("--cls", type=int, default=19)
    ap.add_argument("--conf", type=float, default=0.5, help="umbral del APK (config.ts CONFIDENCE_THRESHOLD)")
    ap.add_argument("--benchmark-json", default=str(ROOT.parent / "informes/benchmark_a25_20260826_fullres.json"))
    ap.add_argument("--photos", default=str(ROOT.parent / "app-benchmark/assets/photos"))
    ap.add_argument("--val-dir", default=str(ROOT / "data/val_clean"))
    ap.add_argument("--out", default=str(ROOT.parent / "informes" / f"paridad_segmentador_{date.today().strftime('%Y%m%d')}"))
    a = ap.parse_args()

    from core.segmenter import CowSegmenter
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    pt = CowSegmenter(a.pt, cow_class_id=a.cls, min_confidence=a.conf, device="cpu")
    lite = LiteRTCowSegmenter(a.tflite, cow_class_id=a.cls, min_confidence=a.conf)
    meta = {"fecha": date.today().isoformat(), "conf": a.conf, "cls": a.cls,
            "pt": {"ruta": a.pt, "sha256_16": hashlib.sha256(Path(a.pt).read_bytes()).hexdigest()[:16]},
            "tflite": {"ruta": a.tflite, "sha256_16": hashlib.sha256(Path(a.tflite).read_bytes()).hexdigest()[:16]}}

    # ---------- A) benchmark A25 ----------
    rows_a = []
    bench = json.load(open(a.benchmark_json))
    device = {s["foto"]: s for s in bench["segmentation"] if s["modelo"] == "fp32"}
    for foto, dev in sorted(device.items()):
        p = Path(a.photos) / f"photo_{foto}.jpeg"
        if not p.exists():
            print(f"aviso: falta {p}")
            continue
        img = cv2.imread(str(p))
        ld = lite.detections(img)
        lsel = max(ld, key=lambda d: d.area_px) if ld else None
        psel = largest(pt.segment(img))
        bbox_dev = dev["selected_bbox_original_px"]
        rows_a.append({
            "foto": foto,
            "dets_a25": dev["cow_dets"], "dets_pc_litert": len(ld), "dets_pt": len(pt.segment(img)),
            "area_a25": dev["mask_area_px"], "area_pc_litert": lsel.area_px if lsel else 0,
            "dif_pc_litert_vs_a25_pct": round(pct(lsel.area_px, dev["mask_area_px"]), 3) if lsel else None,
            "area_pt": psel.area_px if psel else 0,
            "dif_litert_vs_pt_pct": round(pct(lsel.area_px, psel.area_px), 3) if lsel and psel else None,
            "iou_litert_vs_pt": round(iou(lsel.mask, psel.mask), 4) if lsel and psel else None,
            "conf_a25": round(dev["selected_confidence"], 4), "conf_pc_litert": round(lsel.confidence, 4) if lsel else None,
            "bbox_maxdif_px": round(max(abs(x - y) for x, y in zip(lsel.bbox_original, bbox_dev)), 2) if lsel and bbox_dev else None,
        })
        print(f"{foto:12} A25 {dev['mask_area_px']:7d} px | PC-LiteRT {rows_a[-1]['area_pc_litert']:7d} px "
              f"({rows_a[-1]['dif_pc_litert_vs_a25_pct']:+.3f}%) | .pt {rows_a[-1]['area_pt']:7d} px "
              f"(LiteRT vs pt {rows_a[-1]['dif_litert_vs_pt_pct']:+.2f}%)")

    # ---------- B) val manual ----------
    rows_b = []
    val = Path(a.val_dir)
    for r in csv.DictReader(open(val / "manifest.csv")):
        ip = next((val / "images").glob(f"{r['qid']}.*"))
        img = cv2.imread(str(ip))
        h, w = img.shape[:2]
        gts = load_gt_pngs(val / "masks", r["qid"], w, h)
        ps, ls = pt.segment(img), lite.segment(img)
        psel, lsel = largest(ps), largest(ls)
        row = {"qid": r["qid"], "stratum": r["stratum"], "cow_id": r["cow_id"], "dets_pt": len(ps), "dets_litert": len(ls),
               "area_pt": psel.area_px if psel else 0, "area_litert": lsel.area_px if lsel else 0}
        row["dif_area_pct"] = round(pct(row["area_litert"], row["area_pt"]), 2) if psel and lsel else None
        row["iou_pt_vs_litert"] = round(iou(psel.mask, lsel.mask), 4) if psel and lsel else None
        row["pt_eligio_objetivo"] = bool(psel is not None and gts and iou(psel.mask, gts[0]) >= 0.5)
        row["litert_eligio_objetivo"] = bool(lsel is not None and gts and iou(lsel.mask, gts[0]) >= 0.5)
        row["iou_objetivo_pt"] = round(iou(psel.mask, gts[0]), 4) if psel and gts else 0.0
        row["iou_objetivo_litert"] = round(iou(lsel.mask, gts[0]), 4) if lsel and gts else 0.0
        rows_b.append(row)

    # ---------- resumen ----------
    def stats(vals):
        v = np.array([x for x in vals if x is not None], dtype=float)
        return {"n": int(v.size), "media": round(float(v.mean()), 3), "abs_media": round(float(np.abs(v).mean()), 3),
                "abs_max": round(float(np.abs(v).max()), 3)} if v.size else {"n": 0}

    summary = {
        "meta": meta,
        "A_benchmark_a25": {
            "n_fotos": len(rows_a),
            "dets_iguales_pc_vs_a25": int(sum(r["dets_a25"] == r["dets_pc_litert"] for r in rows_a)),
            "dif_area_pc_litert_vs_a25_pct": stats([r["dif_pc_litert_vs_a25_pct"] for r in rows_a]),
            "dif_conf_pc_vs_a25_abs_max": round(max(abs(r["conf_pc_litert"] - r["conf_a25"]) for r in rows_a if r["conf_pc_litert"] is not None), 5),
            "bbox_maxdif_px_max": max(r["bbox_maxdif_px"] for r in rows_a if r["bbox_maxdif_px"] is not None),
            "dif_area_litert_vs_pt_pct": stats([r["dif_litert_vs_pt_pct"] for r in rows_a]),
            "iou_litert_vs_pt": stats([r["iou_litert_vs_pt"] for r in rows_a]),
            "criterio_area_le_1pct": bool(all(abs(r["dif_litert_vs_pt_pct"]) <= 1.0 for r in rows_a if r["dif_litert_vs_pt_pct"] is not None)),
        },
        "B_val_manual": {},
    }
    for s in ("facil", "media", "dificil", "total"):
        sub = [r for r in rows_b if s == "total" or r["stratum"] == s]
        summary["B_val_manual"][s] = {
            "n": len(sub),
            "dets_iguales": int(sum(r["dets_pt"] == r["dets_litert"] for r in sub)),
            "iou_pt_vs_litert": stats([r["iou_pt_vs_litert"] for r in sub]),
            "dif_area_pct": stats([r["dif_area_pct"] for r in sub]),
            "misma_decision_objetivo": int(sum(r["pt_eligio_objetivo"] == r["litert_eligio_objetivo"] for r in sub)),
            "pt_eligio_objetivo": int(sum(r["pt_eligio_objetivo"] for r in sub)),
            "litert_eligio_objetivo": int(sum(r["litert_eligio_objetivo"] for r in sub)),
            "iou_objetivo_pt": round(float(np.mean([r["iou_objetivo_pt"] for r in sub])), 3),
            "iou_objetivo_litert": round(float(np.mean([r["iou_objetivo_litert"] for r in sub])), 3),
        }

    for name, rows in (("paridad_benchmark_a25.csv", rows_a), ("paridad_val_manual.csv", rows_b)):
        with open(out / name, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    (out / "resumen.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))

    A, B = summary["A_benchmark_a25"], summary["B_val_manual"]
    md = [f"# Paridad del segmentador — {meta['fecha']}", "",
          f".pt `{Path(a.pt).name}` (sha256 {meta['pt']['sha256_16']}…) vs LiteRT `{Path(a.tflite).name}` (sha256 {meta['tflite']['sha256_16']}…), "
          f"conf {a.conf}, clase {a.cls}, selección = mayor área.", "",
          "## A. Emulación LiteRT en PC vs Galaxy A25 (10 fotos del benchmark, 26 ago 2026)", "",
          f"- Mismo número de detecciones en {A['dets_iguales_pc_vs_a25']} de {A['n_fotos']} fotos.",
          f"- Área PC-LiteRT vs A25: media {A['dif_area_pc_litert_vs_a25_pct'].get('media')} %, |máx| {A['dif_area_pc_litert_vs_a25_pct'].get('abs_max')} %.",
          f"- Confianza: |dif| máx {A['dif_conf_pc_vs_a25_abs_max']}. Caja: |dif| máx {A['bbox_maxdif_px_max']} px.",
          "", "## A'. LiteRT vs .pt en las mismas 10 fotos", "",
          f"- Área: media {A['dif_area_litert_vs_pt_pct'].get('media')} %, |media| {A['dif_area_litert_vs_pt_pct'].get('abs_media')} %, |máx| {A['dif_area_litert_vs_pt_pct'].get('abs_max')} %. "
          f"Criterio ≤ 1 %: {'PASA' if A['criterio_area_le_1pct'] else 'FALLA'}.",
          f"- IoU entre máscaras: media {A['iou_litert_vs_pt'].get('media')}, mín {round(min(r['iou_litert_vs_pt'] for r in rows_a if r['iou_litert_vs_pt'] is not None), 4)}.",
          "", "## B. .pt vs LiteRT en las 40 imágenes manuales", "",
          "| estrato | n | mismas detecciones | IoU pt↔LiteRT (media / mín) | dif. área % (media / \\|máx\\|) | misma decisión objetivo | eligió objetivo pt / LiteRT | IoU objetivo pt / LiteRT |",
          "|---|---|---|---|---|---|---|---|"]
    for s in ("facil", "media", "dificil", "total"):
        d = B[s]
        sub = [r for r in rows_b if s == "total" or r["stratum"] == s]
        mn = min((r["iou_pt_vs_litert"] for r in sub if r["iou_pt_vs_litert"] is not None), default=None)
        md.append(f"| {s} | {d['n']} | {d['dets_iguales']} | {d['iou_pt_vs_litert'].get('media')} / {mn} | "
                  f"{d['dif_area_pct'].get('media')} / {d['dif_area_pct'].get('abs_max')} | {d['misma_decision_objetivo']} | "
                  f"{d['pt_eligio_objetivo']} / {d['litert_eligio_objetivo']} | {d['iou_objetivo_pt']} / {d['iou_objetivo_litert']} |")
    (out / "resumen.md").write_text("\n".join(md) + "\n")
    print("\n" + "\n".join(md[4:]))
    print(f"\nSalida: {out}")


if __name__ == "__main__":
    raise SystemExit(main())
