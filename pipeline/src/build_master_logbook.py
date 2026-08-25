"""Cross-reference the weights CSV against the photo folders -> master logbook.

    python3 src/build_master_logbook.py
"""
from __future__ import annotations
import csv, re, sys
from collections import Counter, defaultdict
from pathlib import Path

LB_TO_KG = 0.453592
field = Path("data/field")
csvp = field / "peso_bovinos_finca_primavera.csv"
grouped = field / "raw" / "_grouped"

rows = list(csv.DictReader(open(csvp)))
labels = [r["Label"].strip() for r in rows]
dups = {l for l, c in Counter(labels).items() if c > 1}

folder_counts: dict[str, int] = defaultdict(int)
folder_variants: dict[str, list] = defaultdict(list)
for d in sorted(grouped.iterdir()):
    if not d.is_dir() or d.name.startswith("_"):
        continue
    m = re.match(r"(\d+)", d.name)
    if not m:
        continue
    arete = m.group(1)
    n = len([p for p in d.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png")])
    folder_counts[arete] += n
    folder_variants[arete].append(d.name)

weight_aretes = set(labels)
folder_aretes = set(folder_counts)

out = []
for r in rows:
    a = r["Label"].strip(); lb = float(r["Weight (LB)"])
    out.append({
        "arete": a, "nombre": r["Name"].strip(), "peso_lb": lb,
        "peso_kg": round(lb * LB_TO_KG, 1),
        "tiene_fotos": "si" if a in folder_aretes else "NO",
        "n_fotos": folder_counts.get(a, 0),
        "carpetas": ";".join(folder_variants.get(a, [])),
        "arete_duplicado": "SI" if a in dups else "",
    })

master = field / "master_logbook.csv"
with open(master, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)

usable = [r for r in out if r["tiene_fotos"] == "si" and r["arete"] not in dups]
w_no_photo = [r for r in out if r["tiene_fotos"] == "NO"]
photo_no_weight = sorted(folder_aretes - weight_aretes)

print(f"Total en lista de pesos: {len(out)} (kg {min(r['peso_kg'] for r in out)}-{max(r['peso_kg'] for r in out)})")
print(f"\n✅ USABLES (foto + peso, sin conflicto): {len(usable)}")
print(f"⚠️  Aretes DUPLICADOS (resolver): {sorted(dups)}")
print(f"❌ Peso SIN fotos: {[(r['arete'], r['nombre']) for r in w_no_photo]}")
print(f"❓ Fotos SIN peso (carpetas sin match): {photo_no_weight}")
print(f"\nmaster -> {master}")
