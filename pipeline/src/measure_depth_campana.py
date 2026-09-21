"""Profundidad corporal proyectada de las fotografías a 3 m de la campaña de calibración.

Para cada fotografía de `medidas_app_3m_20260912.csv` calcula `D_media` con `core.depth`, la referencia
Python de `app/src/vision/depth.ts`, sobre la máscara que produce la ruta de la aplicación y con la
escala `cm_per_px` de js-aruco2 que el propio CSV declara.

Las máscaras son las de la ruta de la aplicación (jpeg-js + LiteRT FP32 + `segment.ts`), no las de una
decodificación con libjpeg: sobre ocho fotografías de control las dos rutas dan la misma `D_media` en
siete y difieren 3.3·10⁻³ cm en una, porque el área cambia en torno al 0.1 % con el decodificador
mientras la profundidad del tronco no. Esa diferencia es pequeña pero no es cero, y el bundle se
calibra con la magnitud que el teléfono mide, no con una aproximación.

Cada máscara llega en un `.npz` por fotografía, con `shape` y `bits` (`np.packbits` de la máscara fila
a fila en píxeles originales), el formato que escribe el arnés que reproduce la ruta de la aplicación
en computadora. El directorio se pasa con `--mascaras` o la variable `BOVINO_CAMPANA_MASCARAS`; queda
fuera del repositorio, igual que las fotografías originales.

    python3 src/measure_depth_campana.py --mascaras <dir> --out ../pipeline/data/field/campana_20260912/profundidad_app_3m_20260912.csv
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from core.depth import profundidad_media  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/field/campana_20260912"
MEDIDAS_DEFAULT = DATA / "medidas_app_3m_20260912.csv"
OUT_DEFAULT = DATA / "profundidad_app_3m_20260912.csv"
MASCARAS_DIR = (
    Path(os.environ["BOVINO_CAMPANA_MASCARAS"]).expanduser()
    if os.environ.get("BOVINO_CAMPANA_MASCARAS")
    else None
)
CAMPOS = ["foto", "fila", "cm_per_px", "estado_profundidad", "d_media_cm", "d_max_cm",
          "l_gate_cm", "kernel_px", "lo", "hi", "c0", "c1", "ancho_componente_px",
          "mask_area_px", "sha256_mascara"]


def desempaquetar(npz: Path) -> np.ndarray:
    d = np.load(npz)
    shape = tuple(int(v) for v in d["shape"])
    return np.unpackbits(d["bits"])[: shape[0] * shape[1]].reshape(shape).astype(np.uint8)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--medidas", type=Path, default=MEDIDAS_DEFAULT)
    ap.add_argument("--mascaras", type=Path, default=MASCARAS_DIR,
                    help="directorio con un .npz por fotografía; fuera del repositorio")
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    a = ap.parse_args(argv)

    if a.mascaras is None:
        raise ValueError("indica --mascaras o define BOVINO_CAMPANA_MASCARAS")

    with a.medidas.open(encoding="utf-8-sig", newline="") as f:
        medidas = list(csv.DictReader(f))

    filas, faltan, sin_escala = [], [], 0
    for m in medidas:
        npz = a.mascaras / (Path(m["foto"]).stem + ".npz")
        escala = m["cm_per_px"].strip()
        fila = {c: "" for c in CAMPOS}
        fila["foto"], fila["fila"], fila["cm_per_px"] = m["foto"], m["fila"], escala

        if not escala or float(escala) <= 0:
            fila["estado_profundidad"] = "sin_escala"
            sin_escala += 1
            filas.append(fila)
            continue
        if not npz.exists():
            faltan.append(m["foto"])
            fila["estado_profundidad"] = "sin_mascara"
            filas.append(fila)
            continue

        mask = desempaquetar(npz)
        d = profundidad_media(mask, float(escala))
        fila["estado_profundidad"] = d.status
        fila["mask_area_px"] = int(mask.sum())
        fila["sha256_mascara"] = hashlib.sha256(np.packbits(mask.ravel()).tobytes()).hexdigest()
        if d.ok:
            fila.update({
                "d_media_cm": repr(d.d_media_cm), "d_max_cm": repr(d.d_max_cm),
                "l_gate_cm": repr(d.l_gate_cm), "kernel_px": d.kernel_px,
                "lo": d.lo, "hi": d.hi, "c0": d.c0, "c1": d.c1,
                "ancho_componente_px": d.ancho_componente_px,
            })
        filas.append(fila)

    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        w.writeheader()
        w.writerows(filas)

    ok = sum(1 for r in filas if r["estado_profundidad"] == "ok")
    print(f"{len(filas)} fotografías; {ok} con profundidad medida; {sin_escala} sin escala; "
          f"{len(faltan)} sin máscara")
    if faltan:
        print("sin máscara:", ", ".join(faltan[:10]), file=sys.stderr)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, KeyError, FileNotFoundError) as e:
        print("ERROR:", e, file=sys.stderr)
        sys.exit(1)
