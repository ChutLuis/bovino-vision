"""Revisa y corrige a mano las mascaras con escala dudosa (outliers) — o todas.

En vez de descartar las medidas atipicas, te las abre UNA POR UNA en el pincel para
que las redibujes bien (marcador en el plano, vaca de perfil). Asi aseguras las mejores
mascaras en vez de confiar en el auto o botarlas.

    python3 src/review_masks.py --dir data/field/raw/_grouped/7260     # outliers de esa vaca
    python3 src/review_masks.py --all                                  # outliers de todas
    python3 src/review_masks.py --dir <...> --mode all                 # re-revisar TODAS sus fotos
"""
from __future__ import annotations
import argparse, csv, re, statistics as st, subprocess, sys
from collections import defaultdict
from pathlib import Path

field = Path("data/field")
grouped = field / "raw" / "_grouped"
MIN_LEN, MAX_LEN, DEV = 110.0, 185.0, 0.18


def length(r):
    try:
        return float(r["body_length_cm"])
    except (ValueError, TypeError, KeyError):
        return None


def to_review(folder: Path, mode: str) -> list[str]:
    csvp = folder / "medidas.csv"
    if not csvp.exists():
        return []
    rows = list(csv.DictReader(open(csvp)))
    vals = [length(r) for r in rows if length(r) is not None]
    if not vals:
        return []
    med = st.median(vals)
    out = []
    for r in rows:
        L = length(r)
        if L is None:
            continue
        if mode == "all" or not (MIN_LEN <= L <= MAX_LEN) or abs(L - med) > DEV * med:
            out.append(r["photo"])
    return out


def review(folder: Path, cow_id: str, mode: str):
    outs = to_review(folder, mode)
    if not outs:
        print(f"  {folder.name}: nada que revisar")
        return 0
    print(f"\n=== {folder.name} ({cow_id}): {len(outs)} a redibujar ===")
    subprocess.run([sys.executable, "src/draw_mask.py", "--dir", str(folder), "--cow-id", cow_id,
                    "--marker-size-cm", "15", "--photos", ",".join(outs)])
    return len(outs)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--mode", choices=["outliers", "all"], default="outliers")
    a = ap.parse_args()

    if a.all:
        master = list(csv.DictReader(open(field / "master_logbook.csv")))
        fold = defaultdict(list)
        for dd in grouped.iterdir():
            if dd.is_dir() and not dd.name.startswith("_"):
                mm = re.match(r"(\d+)", dd.name)
                if mm:
                    fold[mm.group(1)].append(dd)
        total = 0
        for r in master:
            if r["tiene_fotos"] != "si":
                continue
            for dd in fold.get(r["arete"], []):
                total += review(dd, r["arete"], a.mode) or 0
        print(f"\nRevisadas. (modo: {a.mode})")
    else:
        if not a.dir:
            ap.error("usa --dir <carpeta> o --all")
        d = Path(a.dir)
        review(d, re.match(r"(\d+)", d.name).group(1), a.mode)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
