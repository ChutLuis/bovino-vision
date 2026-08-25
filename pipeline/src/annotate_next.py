"""Progreso + abre la siguiente vaca que aun no llega al target de mascaras.

Solo necesitas ~N buenas mascaras por vaca (no todas). Una vez que una vaca llega
al target, sale de la cola. Corre auto_mask primero; esto te lleva por lo que falta.

    python3 src/annotate_next.py                 # target 5 por defecto
    python3 src/annotate_next.py --target 4
    python3 src/annotate_next.py --status         # solo el tablero
"""
from __future__ import annotations
import argparse, csv, re, subprocess, sys
from collections import defaultdict
from pathlib import Path

field = Path("data/field")
grouped = field / "raw" / "_grouped"
master = list(csv.DictReader(open(field / "master_logbook.csv")))

folders: dict[str, list] = defaultdict(list)
for d in grouped.iterdir():
    if d.is_dir() and not d.name.startswith("_"):
        m = re.match(r"(\d+)", d.name)
        if m:
            folders[m.group(1)].append(d)


def count(arete: str, sub: str) -> int:
    return sum(len(list((d / sub).glob("*.jpg"))) for d in folders.get(arete, []))


ap = argparse.ArgumentParser()
ap.add_argument("--status", action="store_true")
ap.add_argument("--target", type=int, default=5, help="mascaras objetivo por vaca")
a = ap.parse_args()
T = a.target

usable = [r for r in master if r["tiene_fotos"] == "si"]
rows = [(r["arete"], r["nombre"], count(r["arete"], "listas"), count(r["arete"], "revisar"),
         count(r["arete"], "sin_marcador"), r["arete_duplicado"] == "SI") for r in usable]

done = [x for x in rows if x[2] >= T or (x[3] == 0 and x[2] > 0)]
pending = [x for x in rows if x[2] < T and x[3] > 0]
sin_procesar = [x for x in rows if x[2] + x[3] + x[4] == 0]
tot_listas = sum(x[2] for x in rows)

print(f"\n=== PROGRESO (target {T}/vaca) ===")
print(f"  Vacas listas: {len(done)}/{len(usable)}   |   medidas totales: {tot_listas}")
print(f"  Vacas que aun necesitan dibujo: {len(pending)}")
if sin_procesar:
    print(f"  Sin procesar (corre auto_mask --all): {len(sin_procesar)}")
print()
if pending:
    print("FALTAN (a dibujar a mano hasta llegar al target):")
    for ar, nm, nl, nr, ns, dup in sorted(pending, key=lambda x: x[2]):
        print(f"  {ar:6} {nm:18} {nl}/{T} listas  ({nr} en revisar)" + ("  [dup]" if dup else ""))

if a.status:
    sys.exit(0)
if not pending:
    print("\nTodas al target. Corre:  python3 src/build_dataset.py")
    sys.exit(0)

nxt = sorted(pending, key=lambda x: x[2])[0]
ar, nm = nxt[0], nxt[1]
best = max(folders[ar], key=lambda d: len(list((d / "revisar").glob("*.jpg"))))
print(f"\nAbriendo -> {ar} ({nm})  faltan {T - nxt[2]} para el target.  carpeta: {best}")
print(f"Dibuja ~{T - nxt[2]} buenas, termina con 'q' (para automatico al llegar al target).\n")
subprocess.run([sys.executable, "src/draw_mask.py", "--dir", str(best), "--cow-id", ar,
                "--marker-size-cm", "15", "--target", str(T)])
print(f"\nListo {ar}. Corre 'python3 src/annotate_next.py' otra vez para seguir.")
