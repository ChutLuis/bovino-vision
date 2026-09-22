"""Repetibilidad entre fotografías del mismo animal de los dos predictores de peso de la campaña.

Sobre las fotografías preseleccionadas a 3 m que la ruta de la aplicación aceptó y para las que existe medida de
profundidad, compara cuánto varía el peso predicho al repetir la fotografía del mismo animal con el modelo de área
(`W = a·A^b`) y con el de profundidad corporal proyectada (`W = a·D`). Para cada predictor calcula el ICC(1) de una
vía del logaritmo del predictor (que coincide con el del logaritmo del peso para cualquier modelo alométrico), el
coeficiente de variación del peso predicho por animal y su rango (máximo menos mínimo) en kg. El peso se predice
con el ajuste completo de cada modelo, tomado de su `weight_model.json`.

Escribe `repetibilidad_3m.csv` (una fila por animal) y `repetibilidad_3m.md` (resumen) en el directorio de salida.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/field/campana_20260912"
INFORMES = ROOT.parent / "informes/campana_20260912"


def leer_csv(path: Path) -> list[dict[str, str]]:
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def icc1(grupos: list[list[float]]) -> float | None:
    """ICC(1) de una vía para grupos desbalanceados: (MSB − MSW) / (MSB + (n0 − 1)·MSW)."""
    grupos = [g for g in grupos if len(g) > 0]
    N, k = sum(map(len, grupos)), len(grupos)
    if k < 2 or N <= k:
        return None
    media = float(np.mean([v for g in grupos for v in g]))
    msb = sum(len(g) * (float(np.mean(g)) - media) ** 2 for g in grupos) / (k - 1)
    msw = sum(sum((v - float(np.mean(g))) ** 2 for v in g) for g in grupos) / (N - k)
    n0 = (N - sum(len(g) ** 2 for g in grupos) / N) / (k - 1)
    denominador = msb + (n0 - 1) * msw
    return float((msb - msw) / denominador) if denominador > 0 else None


def resumir(valores: dict[str, list[float]], a: float, b: float) -> dict:
    """Repetibilidad de un predictor: `valores` es fila -> lista de medidas del predictor por fotografía."""
    pesos = {fid: [a * v ** b for v in vals] for fid, vals in valores.items()}
    cv = {fid: float(np.std(p, ddof=1) / np.mean(p) * 100) for fid, p in pesos.items() if len(p) > 1}
    rango = {fid: float(max(p) - min(p)) for fid, p in pesos.items() if len(p) > 1}
    return {
        "n_fotos": int(sum(map(len, valores.values()))),
        "n_animales": len(valores),
        "icc1_log": icc1([[math.log(v) for v in vals] for vals in valores.values()]),
        "cv_peso_pct": cv,
        "rango_peso_kg": rango,
    }


def texto(res: dict[str, dict], nombres: dict[str, str]) -> str:
    filas = ["# Repetibilidad de los dos predictores entre fotografías del mismo animal", "",
             "Fotografías preseleccionadas a 3 m aceptadas por la ruta de la aplicación y con profundidad medida; el peso "
             "de cada fotografía se predice con el ajuste completo de cada modelo. El ICC(1) del logaritmo del predictor "
             "es el del logaritmo del peso predicho. El coeficiente de variación y el rango del peso predicho por animal "
             "son la dispersión que ve el usuario al repetir la fotografía.", "",
             "| Predictor | Fotografías | Animales | ICC(1) log | CV del peso: mediana | CV: máximo | Rango del peso: mediana | Rango: máximo | Rango: medio |",
             "|---|---|---|---|---|---|---|---|---|"]
    for etiqueta, r in res.items():
        cv, rg = list(r["cv_peso_pct"].values()), list(r["rango_peso_kg"].values())
        filas.append(f"| {etiqueta} | {r['n_fotos']} | {r['n_animales']} | {r['icc1_log']:.3f} | {np.median(cv):.2f} % | {max(cv):.2f} % | "
                     f"{np.median(rg):.1f} kg | {max(rg):.1f} kg | {np.mean(rg):.1f} kg |")
    peor = {etiqueta: max(r["rango_peso_kg"], key=r["rango_peso_kg"].get) for etiqueta, r in res.items()}
    filas += ["", "Animal con mayor rango por predictor: " + "; ".join(
        f"{etiqueta}: fila {fid} ({nombres.get(fid, '')}), {res[etiqueta]['rango_peso_kg'][fid]:.1f} kg" for etiqueta, fid in peor.items()) + ".",
        "", "Detalle por animal en `repetibilidad_3m.csv`."]
    return "\n".join(filas) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--medidas", type=Path, default=DATA / "medidas_app_3m_20260912.csv", help="medidas de área de la ruta de la app")
    ap.add_argument("--profundidad", type=Path, default=DATA / "profundidad_app_3m_20260912.csv", help="profundidad por fotografía")
    ap.add_argument("--modelo-area", type=Path, default=INFORMES / "peso/weight_model.json")
    ap.add_argument("--modelo-profundidad", type=Path, default=INFORMES / "peso_profundidad/weight_model.json")
    ap.add_argument("--out", type=Path, default=INFORMES / "peso_profundidad", help="directorio de salida")
    a = ap.parse_args(argv)

    medidas = leer_csv(a.medidas)
    profundidad = {r["foto"]: r for r in leer_csv(a.profundidad) if r["estado_profundidad"] == "ok"}
    aceptada = lambda m: m["estado"] == "ok" and m["revision_visual"] == "aceptar" and m["area_cm2"].strip()  # noqa: E731
    fotos = [m for m in sorted(medidas, key=lambda m: (int(m["fila"]), int(m["rango_3m"]))) if aceptada(m) and m["foto"] in profundidad]
    if not fotos:
        print("sin fotografías aceptadas con profundidad medida", file=sys.stderr)
        return 2
    filas = sorted({m["fila"] for m in fotos}, key=int)
    nombres = {m["fila"]: m["nombre"] for m in fotos}
    area = {fid: [float(m["area_cm2"]) for m in fotos if m["fila"] == fid] for fid in filas}
    depth = {fid: [float(profundidad[m["foto"]]["d_media_cm"]) for m in fotos if m["fila"] == fid] for fid in filas}
    ma = json.loads(a.modelo_area.read_text())
    mp = json.loads(a.modelo_profundidad.read_text())
    res = {"área W = a·A^b": resumir(area, ma["a"], ma["b"]), "profundidad W = a·D": resumir(depth, mp["a"], mp["b"])}

    a.out.mkdir(parents=True, exist_ok=True)
    ra, rp = res["área W = a·A^b"], res["profundidad W = a·D"]
    with (a.out / "repetibilidad_3m.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["fila", "nombre", "n_fotos", "cv_peso_area_pct", "rango_peso_area_kg", "cv_peso_profundidad_pct", "rango_peso_profundidad_kg"])
        for fid in filas:
            w.writerow([fid, nombres[fid], len(area[fid]), f"{ra['cv_peso_pct'].get(fid, float('nan')):.3f}", f"{ra['rango_peso_kg'].get(fid, float('nan')):.2f}",
                        f"{rp['cv_peso_pct'].get(fid, float('nan')):.3f}", f"{rp['rango_peso_kg'].get(fid, float('nan')):.2f}"])
    md = texto(res, nombres)
    (a.out / "repetibilidad_3m.md").write_text(md)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
