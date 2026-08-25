"""Assemble the training dataset, joined to weights (kg), with outlier filtering.

Por defecto agrega UNA fila por vaca (mediana de sus fotos buenas) — robusto al ruido
de escala y acorde a que hay un peso por vaca. Usa --por-foto para una fila por foto.

    python3 src/build_dataset.py                 # una fila por vaca (mediana) [recomendado]
    python3 src/build_dataset.py --por-foto       # una fila por foto
    python3 src/train_weight_model.py --csv data/field/dataset.csv --target peso_kg --group cow_id
"""
from __future__ import annotations
import argparse, csv
import statistics as st
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--por-foto", action="store_true", help="una fila por foto (default: una por vaca)")
a = ap.parse_args()

field = Path("data/field")
master = {r["arete"]: r for r in csv.DictReader(open(field / "master_logbook.csv"))}

FEATURES = ["body_length_cm", "height_cm", "chest_depth_cm", "lateral_area_cm2", "aspect_ratio", "fill_ratio"]
MIN_LEN, MAX_LEN, DEV = 110.0, 185.0, 0.18

rows = []
for pattern in ("*/medidas.csv", "*/sam_features.csv"):
    for fcsv in sorted((field / "raw" / "_grouped").glob(pattern)):
        for r in csv.DictReader(open(fcsv)):
            cid = str(r.get("cow_id", "")).strip()
            m = master.get(cid)
            if not m or m["arete_duplicado"] == "SI" or m["peso_kg"] in ("", None):
                continue
            try:
                feats = {f: float(r[f]) for f in FEATURES}
            except (ValueError, TypeError, KeyError):
                continue
            rows.append({"photo": r["photo"], "cow_id": cid, "nombre": m["nombre"],
                         "peso_kg": float(m["peso_kg"]), **feats})

if not rows:
    raise SystemExit("Sin features aun. Anota vacas con auto_mask / draw_mask primero.")

# 1) rango plausible + 2) outliers por vaca (lejos de la mediana = marcador fuera de plano)
n0 = len(rows)
rows = [r for r in rows if MIN_LEN <= r["body_length_cm"] <= MAX_LEN]
by: dict[str, list] = {}
for r in rows:
    by.setdefault(r["cow_id"], []).append(r)
clean = []
for cid, rs in by.items():
    med = st.median([r["body_length_cm"] for r in rs])
    clean += [r for r in rs if abs(r["body_length_cm"] - med) <= DEV * med]
dropped = n0 - len(clean)
rows = clean

out_csv = field / "dataset.csv"
if a.por_foto:
    final = rows
else:
    # una fila por vaca: mediana de cada feature
    grp: dict[str, list] = {}
    for r in rows:
        grp.setdefault(r["cow_id"], []).append(r)
    final = []
    for cid, rs in grp.items():
        row = {"cow_id": cid, "nombre": rs[0]["nombre"], "peso_kg": rs[0]["peso_kg"], "n_fotos": len(rs)}
        for f in FEATURES:
            row[f] = round(st.median([r[f] for r in rs]), 2)
        final.append(row)

with open(out_csv, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(final[0].keys())); w.writeheader(); w.writerows(final)

cows = sorted({r["cow_id"] for r in rows})
modo = "una fila por foto" if a.por_foto else "una fila por vaca (mediana)"
print(f"dataset ({modo}): {len(final)} filas de {len(cows)} vacas  ({dropped} fotos atipicas filtradas) -> {out_csv}")
print(f"vacas: {', '.join(cows)}")
if len(cows) < 5:
    print(f"\n(necesitas >=5 vacas para k-fold; llevas {len(cows)})")
