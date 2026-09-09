"""Evaluación de segmentadores contra el conjunto de validación anotado a mano.

Referencia: data/val_clean (manifest.csv, images/, masks/{qid}_inst{k}.png). Los PNG son
las máscaras pintadas en annotate_val.py; inst0 es la vaca objetivo (la que se pesó). Con
`--gt polygon` se usan los labels YOLO-seg (una instancia por línea) en lugar de los PNG.

Todos los modelos se evalúan con el mismo conf, imgsz y regla de selección (mayor área,
como el pipeline de peso). Por imagen se reporta si el modelo eligió la vaca objetivo, el
IoU y el error de área de esa vaca, el IoU emparejado por instancia, el recall de
instancias con IoU >= 0.5 y los falsos positivos. Se agrega por estrato y se calcula un
IC95 bootstrap remuestreando ANIMALES (no fotos) para la diferencia contra el primer modelo.

    python3 src/eval_finetuned_iou.py                       # preentrenado vs afinado jun-2026
    python3 src/eval_finetuned_iou.py --models pre=models/yolo26n-seg.pt:19 \
        nuevo=runs/segment/runs/seg_finetune_jersey/weights/best.pt:0 --visual

Salida en --out: por_imagen.csv, resumen.json, resumen.md y, con --visual, img/{qid}.jpg
(paneles: manual | modelo 1 | modelo 2 ...) e index.html.
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
from core.seg_eval import (bootstrap_paired_by_group, evaluate_image, greedy_match,  # noqa: E402
                           load_gt_pngs, load_gt_polygons)

ROOT = Path(__file__).resolve().parent.parent
ESTRATOS = ("facil", "media", "dificil")
PANEL_W = 560
COL_GT_TARGET, COL_GT_OTHER = (0, 220, 255), (255, 140, 0)
COL_SEL, COL_OTHER, COL_MISS = (0, 200, 0), (200, 0, 200), (0, 0, 255)


def sha256_16(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def parse_models(specs: list[str]) -> dict[str, tuple[Path, int]]:
    out = {}
    for s in specs:
        name, rest = s.split("=", 1)
        path, cls = rest.rsplit(":", 1)
        out[name] = (Path(path), int(cls))
    return out


def overlay(img, masks_colors, missed=()):
    out = img.copy()
    for m, col in masks_colors:
        layer = np.zeros_like(out)
        layer[m.astype(bool)] = col
        out = cv2.addWeighted(out, 1.0, layer, 0.45, 0)
    for m, _ in masks_colors:
        cnts, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(out, cnts, -1, (255, 255, 255), 2)
    for m in missed:
        cnts, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(out, cnts, -1, COL_MISS, 4)
    return out


def panel(img, lines, color=(255, 255, 255)):
    h = int(img.shape[0] * PANEL_W / img.shape[1])
    small = cv2.resize(img, (PANEL_W, h), interpolation=cv2.INTER_AREA)
    bar = np.full((22 * len(lines) + 10, PANEL_W, 3), 25, np.uint8)
    for i, t in enumerate(lines):
        cv2.putText(bar, t, (8, 18 + 22 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.52, color, 1, cv2.LINE_AA)
    return np.vstack([bar, small])


def compose(panels):
    hmax = max(p.shape[0] for p in panels)
    padded = [np.vstack([p, np.full((hmax - p.shape[0], p.shape[1], 3), 25, np.uint8)]) if p.shape[0] < hmax else p
              for p in panels]
    return np.hstack(padded)


def summarize(rows: list[dict], names: list[str]) -> dict:
    out = {}
    for s in ESTRATOS + ("total",):
        sub = [r for r in rows if s == "total" or r["stratum"] == s]
        out[s] = {}
        for n in names:
            g = lambda k: [r[f"{n}__{k}"] for r in sub]  # noqa: E731
            out[s][n] = {
                "n": len(sub),
                "eligio_objetivo_pct": round(100 * float(np.mean(g("eligio_objetivo"))), 1),
                "sin_deteccion": int(sum(g("sin_deteccion"))),
                "iou_objetivo": round(float(np.mean(g("iou_objetivo"))), 3),
                "pct_iou_objetivo_gt_050": round(100 * float(np.mean([v > 0.5 for v in g("iou_objetivo")])), 1),
                "err_area_medio_pct": round(100 * float(np.mean(g("err_area_objetivo"))), 1),
                "err_area_abs_medio_pct": round(100 * float(np.mean(np.abs(g("err_area_objetivo")))), 1),
                "iou_emparejado": round(float(np.mean(g("iou_emparejado_medio"))), 3),
                "recall_inst_050": round(float(np.mean(g("recall_inst_050"))), 3),
                "fp_total": int(sum(g("fp"))),
            }
    return out


def write_markdown(out: Path, names, models, hashes, summary, boots, args, n_imgs, n_animals):
    L = [f"# IoU contra el conjunto de validación manual — {date.today().isoformat()}", "",
         f"Referencia: `{args.val_dir}` ({n_imgs} imágenes, {n_animals} animales, GT = {args.gt}, objetivo = inst{args.target}). "
         f"conf {args.conf}, imgsz {args.imgsz}, selección = mayor área.", "", "Modelos:", ""]
    for n in names:
        L.append(f"- `{n}`: `{models[n][0]}` (clase {models[n][1]}, sha256 {hashes[n]}…)")
    for s in ("total",) + ESTRATOS:
        L += ["", f"## {s}", "", "| modelo | n | eligió objetivo % | sin detección | IoU objetivo | % IoU>0.5 | err área medio % | |err área| % | IoU emparejado | recall inst | FP |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
        for n in names:
            d = summary[s][n]
            L.append(f"| {n} | {d['n']} | {d['eligio_objetivo_pct']} | {d['sin_deteccion']} | {d['iou_objetivo']} | {d['pct_iou_objetivo_gt_050']} | "
                     f"{d['err_area_medio_pct']} | {d['err_area_abs_medio_pct']} | {d['iou_emparejado']} | {d['recall_inst_050']} | {d['fp_total']} |")
    if boots:
        L += ["", f"## Bootstrap por animal ({args.bootstrap} remuestreos, semilla {args.seed}), diferencia contra `{names[0]}`", ""]
        for n, b in boots.items():
            L.append(f"- `{n}` − `{names[0]}` en IoU objetivo: media {b['iou_objetivo']['dif_media']}, IC95 {b['iou_objetivo']['ic95']}; "
                     f"en error de área: media {b['err_area_objetivo']['dif_media']}, IC95 {b['err_area_objetivo']['ic95']} (n={b['iou_objetivo']['n_grupos']} animales)")
    (out / "resumen.md").write_text("\n".join(L) + "\n")


def write_html(out: Path, rows, names, models, hashes, summary):
    css = ("body{font-family:system-ui;margin:16px;background:#111;color:#eee}table{border-collapse:collapse;margin:8px 0 20px}"
           "td,th{border:1px solid #444;padding:4px 8px;font-size:13px;text-align:right}th{background:#222}td:first-child,th:first-child{text-align:left}"
           "img{max-width:100%;display:block;margin:6px 0 18px;border:1px solid #333}h2{margin-top:32px}.no{color:#f66}.si{color:#6f6}p{max-width:900px}")
    H = [f"<!doctype html><meta charset='utf-8'><title>IoU val manual</title><style>{css}</style>",
         "<h1>Segmentación contra las máscaras manuales</h1>",
         "<p>Izquierda: manual, amarillo = vaca objetivo (inst0), azul = otras. Paneles de modelo: verde = máscara que el pipeline usaría "
         "(mayor área), magenta = otras detecciones, contorno rojo = vaca de referencia que nadie recuperó con IoU ≥ 0.5.</p>",
         "<p>" + "; ".join(f"<b>{n}</b> = {models[n][0].name} (clase {models[n][1]}, sha256 {hashes[n]}…)" for n in names) + "</p>"]
    for s in ("total",) + ESTRATOS:
        H.append(f"<h3>Resumen {s}</h3><table><tr><th>modelo</th><th>n</th><th>eligió objetivo %</th><th>sin detección</th><th>IoU objetivo</th>"
                 "<th>err área %</th><th>|err área| %</th><th>IoU emparejado</th><th>recall inst</th><th>FP</th></tr>")
        for n in names:
            d = summary[s][n]
            H.append(f"<tr><td>{n}</td><td>{d['n']}</td><td>{d['eligio_objetivo_pct']}</td><td>{d['sin_deteccion']}</td><td>{d['iou_objetivo']}</td>"
                     f"<td>{d['err_area_medio_pct']}</td><td>{d['err_area_abs_medio_pct']}</td><td>{d['iou_emparejado']}</td><td>{d['recall_inst_050']}</td><td>{d['fp_total']}</td></tr>")
        H.append("</table>")
    for s in ESTRATOS:
        H.append(f"<h2>{s}</h2>")
        sub = [r for r in rows if r["stratum"] == s]
        if len(names) > 1:
            sub.sort(key=lambda r: r[f"{names[1]}__iou_objetivo"] - r[f"{names[0]}__iou_objetivo"])
        for r in sub:
            cells = " · ".join(
                f"{n}: <span class='{'si' if r[f'{n}__eligio_objetivo'] else 'no'}'>objetivo {'SI' if r[f'{n}__eligio_objetivo'] else 'NO'}</span>, "
                f"IoU {r[f'{n}__iou_objetivo']:.3f}, área {r[f'{n}__err_area_objetivo']*100:+.1f}%, recall {r[f'{n}__recall_inst_050']:.2f}, FP {r[f'{n}__fp']}"
                for n in names)
            H.append(f"<h4>{r['qid']} · {r['cow_id']} · {r['n_gt']} vaca(s)</h4><div>{cells}</div><img src='img/{r['qid']}.jpg' loading='lazy'>")
    (out / "index.html").write_text("\n".join(H))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--val-dir", default=str(ROOT / "data/val_clean"))
    ap.add_argument("--models", nargs="+", metavar="NOMBRE=RUTA.pt:CLASE",
                    default=["preentrenado=models/yolo26n-seg.pt:19", "afinado_jun10=models/yolo26n-seg-finetuned.pt:0"])
    ap.add_argument("--gt", choices=("png", "polygon"), default="png")
    ap.add_argument("--target", type=int, default=0, help="índice de la instancia objetivo (inst0)")
    ap.add_argument("--conf", type=float, default=0.45)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--bootstrap", type=int, default=5000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--visual", action="store_true", help="escribir img/{qid}.jpg e index.html")
    ap.add_argument("--out", default=str(ROOT.parent / "informes" / f"iou_val_manual_{date.today().strftime('%Y%m%d')}"))
    args = ap.parse_args()

    from core.segmenter import CowSegmenter  # import tardío: ultralytics es lento

    val = Path(args.val_dir)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if args.visual:
        (out / "img").mkdir(exist_ok=True)

    models = {n: (p if p.is_absolute() else ROOT / p, c) for n, (p, c) in parse_models(args.models).items()}
    missing = [str(p) for p, _ in models.values() if not p.exists()]
    if missing:
        raise SystemExit(f"no existe(n): {missing}")
    names = list(models)
    hashes = {n: sha256_16(models[n][0]) for n in names}
    segs = {n: CowSegmenter(str(models[n][0]), cow_class_id=models[n][1], min_confidence=args.conf, device=args.device)
            for n in names}

    manifest = list(csv.DictReader(open(val / "manifest.csv")))
    rows = []
    for r in manifest:
        qid, stratum, cow = r["qid"], r["stratum"], r["cow_id"]
        ip = next((val / "images").glob(f"{qid}.*"), None)
        if ip is None:
            print(f"aviso: sin imagen para {qid}")
            continue
        img = cv2.imread(str(ip))
        h, w = img.shape[:2]
        gts = load_gt_pngs(val / "masks", qid, w, h) if args.gt == "png" else load_gt_polygons(val / "labels" / f"{qid}.txt", w, h)
        if not gts:
            print(f"aviso: sin referencia para {qid}")
            continue
        row = {"qid": qid, "stratum": stratum, "cow_id": cow, "n_gt": len(gts), "area_objetivo_px": int(gts[args.target].sum())}
        panels = []
        if args.visual:
            panels.append(panel(overlay(img, [(gts[args.target], COL_GT_TARGET)] + [(g, COL_GT_OTHER) for i, g in enumerate(gts) if i != args.target]),
                                [f"MANUAL  {qid}  [{stratum}]  {cow}", f"instancias={len(gts)}  amarillo=objetivo  azul=otras"]))
        for n in names:
            preds = [c.mask for c in segs[n].segment(img)]
            ev = evaluate_image(preds, gts, target=args.target)
            for k, v in ev.as_row().items():
                row[f"{n}__{k}"] = v
            if args.visual:
                _, matched = greedy_match(preds, gts)
                missed = [g for g, m in zip(gts, matched) if m < 0.5]
                mc = []
                if preds:
                    sel = int(np.argmax([int(m.sum()) for m in preds]))
                    mc = [(preds[sel], COL_SEL)] + [(p, COL_OTHER) for i, p in enumerate(preds) if i != sel]
                l1 = f"{n.upper()}  dets={ev.n_pred}  eligio objetivo: {'SI' if ev.eligio_objetivo else 'NO'}"
                l2 = ("SIN DETECCION" if ev.sin_deteccion else
                      f"IoU obj={ev.iou_objetivo:.3f}  err area={ev.err_area_objetivo*100:+.1f}%  recall inst={ev.recall_inst_050:.2f}  FP={ev.fp}")
                panels.append(panel(overlay(img, mc, missed), [l1, l2], (120, 255, 120) if ev.eligio_objetivo else (80, 80, 255)))
        if args.visual:
            cv2.imwrite(str(out / "img" / f"{qid}.jpg"), compose(panels), [cv2.IMWRITE_JPEG_QUALITY, 82])
        rows.append(row)
        print(f"{qid:22} " + "  ".join(f"{n}: obj={'SI' if row[f'{n}__eligio_objetivo'] else 'NO'} iou={row[f'{n}__iou_objetivo']:.2f}" for n in names))

    summary = summarize(rows, names)
    boots = {}
    if len(names) > 1 and args.bootstrap > 0:
        for n in names[1:]:
            boots[n] = {}
            for metric in ("iou_objetivo", "err_area_objetivo"):
                a = {}
                b = {}
                for r in rows:
                    a.setdefault(r["cow_id"], []).append(r[f"{names[0]}__{metric}"])
                    b.setdefault(r["cow_id"], []).append(r[f"{n}__{metric}"])
                boots[n][metric] = bootstrap_paired_by_group(a, b, n_boot=args.bootstrap, seed=args.seed)

    with open(out / "por_imagen.csv", "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        wr.writeheader()
        wr.writerows(rows)
    meta = {"fecha": date.today().isoformat(), "val_dir": str(val), "gt": args.gt, "target": args.target, "conf": args.conf,
            "imgsz": args.imgsz, "n_imagenes": len(rows), "n_animales": len({r["cow_id"] for r in rows}),
            "modelos": {n: {"ruta": str(models[n][0]), "clase": models[n][1], "sha256_16": hashes[n]} for n in names}}
    (out / "resumen.json").write_text(json.dumps({"meta": meta, "por_estrato": summary, "bootstrap_por_animal": boots}, indent=2, ensure_ascii=False))
    write_markdown(out, names, models, hashes, summary, boots, args, len(rows), meta["n_animales"])
    if args.visual:
        write_html(out, rows, names, models, hashes, summary)

    print()
    print(f"{'modelo':16} {'eligió obj %':>12} {'sin det':>8} {'IoU obj':>8} {'err área %':>10} {'recall inst':>11} {'FP':>4}")
    for n in names:
        d = summary["total"][n]
        print(f"{n:16} {d['eligio_objetivo_pct']:>12} {d['sin_deteccion']:>8} {d['iou_objetivo']:>8} {d['err_area_medio_pct']:>+10} {d['recall_inst_050']:>11} {d['fp_total']:>4}")
    for n, b in boots.items():
        print(f"bootstrap por animal {n} − {names[0]}: IoU obj {b['iou_objetivo']['dif_media']} IC95 {b['iou_objetivo']['ic95']}")
    print(f"\nSalida: {out}")


if __name__ == "__main__":
    raise SystemExit(main())
