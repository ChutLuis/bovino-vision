"""Mide morfometria desde las MASCARAS YA ANOTADAS de las rafagas de la manana.

Reusa el trabajo manual (mascaras/*.png) en vez de re-segmentar. Para cada mascara:
  - localiza su foto en la carpeta -> detecta ArUco (escala, marcador 15cm)
  - measure(mascara, escala) -> features en cm
Mapeo de identidad CORRECTO: carpeta (ultimos 4 del arete) -> inventario -> nombre
-> peso por nombre (pesos_orden_pesaje.csv). Solo vacas PESADAS.

Salida: data/field/features_grouped.csv (1 fila por foto/mascara) -> luego mediana por vaca.

Rutas: las fotos se buscan como build_yolo_seg_dataset.py (--raw, $BOVINO_RAW_GROUPED, ...);
las máscaras por defecto en <raw>/<carpeta>/mascaras/ (los PNG originales de jun 2026) o, con
--masks-root, en <masks-root>/<carpeta>/mascaras/ (p. ej. la regeneración de auto_mask.py --out).

    python3 src/measure_grouped_masks.py                       # máscaras viejas -> features_grouped.csv
    python3 src/measure_grouped_masks.py --masks-root ~/Documents/Thesis_final_raw/mascaras_regen_20260909 \
        --out data/field/features_grouped.csv
"""
from __future__ import annotations
import argparse, csv, re, sys, unicodedata
from pathlib import Path
import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_yolo_seg_dataset import resolve_grouped
from core.aruco import ArucoDetector
from core.calibration import from_marker
from core.morphometry import measure

ROOT = Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--raw", help="directorio _grouped con las fotos de las ráfagas")
ap.add_argument("--masks-root", help="raíz con <carpeta>/mascaras/*.png; por defecto la misma que --raw")
ap.add_argument("--out", default=str(ROOT / "data" / "field" / "features_grouped.csv"))
args = ap.parse_args()

MARKER_CM = 15.0

INV = {
 "ALCIONE":"197264","AMBAR":"236699","AMELIA":"223671","ANITA":"26577","CAMELIA":"197269",
 "CARLINA":"207902","CERECITA":"26579","CERESA":"246502","CHAPARRITA":"207911","CHIQUITA":"223685",
 "CRISALIA":"197257","CRISTY":"73169","DAMITA":"73148","DANESA":"207920","DANIELA":"236687",
 "DIAGIRA":"236688","ESMERALDA":"60771","ESTRELLITA":"197260","FABIOLA":"197272","FORD":"236679",
 "GABY":"223678","GIOCONDA":"223681","IRINA":"207898","IRIS":"236703","KARINA":"236703",
 "KEYLA":"73161","LEONORA":"77859","LUBIANCA":"236694","LUCERO":"223677","LUCY":"236689",
 "MAFER":"236693","MANZANILLA":"223672","MARIITA":"26603","MARIPOSA":"197259","MARIQUITA":"236685",
 "MARTINICA":"26526","MARTITA":"44635","MINERVA":"44627","NAHOMI":"223683","NICOLETA":"26590",
 "NICOL ESTEFANIA":"223682","NOHELIA":"236684","NOHEMI":"236690","NORMANDA":"246503","ODRA":"73159",
 "OSCARINA":"207913","PAULINA":"236700","PERLA":"207915","REALTA":"207903","ROSALINDA":"236681",
 "SELENA":"223679","SENORITA":"207916","SOFIA":"223687","TATY":"236705","VICTORIA":"26533",
 "WADIELA":"77862","YOYI":"207909","ZAFIRO":"236697",
}
ALIAS = {"MARTHITA":"MARTITA","MARTINICE":"MARTINICA","CARINA":"KARINA"}


def norm(s):
    return re.sub(r"\s+"," ",unicodedata.normalize("NFKD",s).encode("ascii","ignore").decode().upper().strip())


last4_to_name = {}
for nm, ar in INV.items():
    last4_to_name.setdefault(ar[-4:], []).append(norm(nm))

field = ROOT / "data" / "field"
# pesos por nombre
peso = {}
for r in csv.DictReader(open(field / "pesos_orden_pesaje.csv")):
    nm = norm(r["Name"]); nm = ALIAS.get(nm, nm)
    peso[nm] = float(r["Weight (LB)"]) * 0.45359237

aruco = ArucoDetector("DICT_6X6_250", allowed_ids=None, min_marker_size_px=18)

OUT = ["photo","folder","cow_id","arete","weight_kg","marker_px","px_per_cm",
       "body_length_cm","height_cm","chest_depth_cm","lateral_area_cm2","aspect_ratio","fill_ratio"]
rows, skip_no_marker, skip = [], 0, 0
cubiertas, sin_peso, ambig = set(), set(), set()

grouped = resolve_grouped(args.raw)
masks_root = Path(args.masks_root).expanduser() if args.masks_root else grouped
print(f"fotos: {grouped}\nmáscaras: {masks_root}")
for d in sorted(grouped.iterdir()):
    if not d.is_dir() or d.name.startswith("_"):
        continue
    m = re.match(r"(\d+)", d.name)
    if not m:
        continue
    last4 = m.group(1)[-4:]
    names = last4_to_name.get(last4, [])
    if not names:
        continue
    # 6703 = IRIS/KARINA (mismo arete, mismo peso 682) -> un solo grupo
    if len(names) > 1:
        if len({round(peso.get(n, -1), 1) for n in names if n in peso}) == 1 and any(n in peso for n in names):
            cow = "/".join(sorted(n for n in names if n in peso))
            w = next(peso[n] for n in names if n in peso)
        else:
            ambig.add(last4); continue
    else:
        cow = names[0]
        if cow not in peso:
            sin_peso.add(cow); continue
        w = peso[cow]

    mdir = masks_root / d.name / "mascaras"
    if not mdir.exists():
        continue
    for mp in sorted(mdir.glob("*.png")):
        # localiza la foto original por stem
        cand = [p for p in d.glob(f"{mp.stem}.*") if p.suffix.lower() in (".jpg", ".jpeg")]
        if not cand:
            skip += 1; continue
        full = cv2.imread(str(cand[0]))
        mask = cv2.imread(str(mp), cv2.IMREAD_GRAYSCALE)
        if full is None or mask is None:
            skip += 1; continue
        if mask.shape[:2] != full.shape[:2]:
            mask = cv2.resize(mask, (full.shape[1], full.shape[0]), interpolation=cv2.INTER_NEAREST)
        mks = aruco.detect(full)
        if not mks:
            skip_no_marker += 1; continue
        mk = max(mks, key=lambda x: x.side_length_px)
        calib = from_marker(mk.side_length_px, MARKER_CM)
        try:
            mo = measure((mask > 127).astype(np.uint8), calib)
        except ValueError:
            skip += 1; continue
        row = {"photo": cand[0].name, "folder": d.name, "cow_id": cow, "arete": INV.get(
                   names[0].title().upper().replace(" ", " "), last4), "weight_kg": round(w, 1),
               "marker_px": round(mk.side_length_px), "px_per_cm": round(calib.px_per_cm, 4)}
        row.update(mo.as_features())
        rows.append(row)
        cubiertas.add(cow)

out_csv = Path(args.out).expanduser()
out_csv.parent.mkdir(parents=True, exist_ok=True)
with open(out_csv, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=OUT); w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k, "") for k in OUT})

print(f"filas (foto/mascara medidas): {len(rows)}")
print(f"vacas PESADAS cubiertas por rafagas: {len(cubiertas)}")
print("  ", ", ".join(sorted(cubiertas)))
print(f"sin marcador (descartadas): {skip_no_marker} | otras descartadas: {skip}")
if sin_peso: print("carpetas con vaca SIN peso (ignoradas):", ", ".join(sorted(sin_peso)))
if ambig:    print("carpetas ambiguas (ignoradas):", ", ".join(sorted(ambig)))
print(f"-> {out_csv}")
