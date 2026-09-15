"""Genera el bundle del modelo de peso (weight_model.json) a partir de las métricas del evaluador.

Lee informes/campana_20260912/metricas.json, escrito por eval_weight_campana.py, y produce el JSON
que la app carga desde app/assets/model_bundle/weight_model.json (app/src/estimation/bundle.ts):

    {"a": 0.41, "b": 0.69,
     "interval": {"sigma_log": 0.08, "t": 2.024, "n": 40, "factor": 1.1781},
     "version": "campana_20260912",
     "fuente": "n=40 vacas; campaña de calibración 12 sep 2026; MAPE LOO 6.50 % (IC95 5.1–8.0)"}

Modelo: peso_kg = a · area_cm2^b, ajustado en log-log sobre una vaca por fila (mediana de sus fotos).

`interval` es el intervalo de predicción al 95 % para un animal nuevo, con n animales de ajuste,
expresado como factor multiplicativo en escala logarítmica:

    factor   = exp(t · sigma_log · sqrt(1 + 1/n))
    peso_min = pred / factor
    peso_max = pred × factor

donde sigma_log = sqrt(RSS/(n−2)) del ajuste completo y t es el cuantil 0.975 de Student con n−2
grados de libertad. Las claves y su redondeo (a, b, sigma_log y factor a 4 decimales; t a 3; n entero)
son el contrato con la app.

La app guarda con cada estimación version_modelo = "peso:<version>;seg:<sha256[0:16] del .tflite>"
(app/src/vision/modelManifest.ts): `version` identifica el ajuste de peso desplegado y cambia con
cada recalibración.

Rechaza con código de salida 2 un metricas.json al que le falten claves, con a, b, sigma_log o t no
positivos, con n < 3, o con factor_ip incoherente con t, sigma_log y n. Escribe solo en la ruta de
--out; copiar el archivo a app/assets/model_bundle/ es un paso aparte y deliberado.

    python3 src/make_weight_bundle.py --metricas informes/campana_20260912/metricas.json --out weight_model.json
    python3 src/make_weight_bundle.py --out weight_model.json --version campana_20260912 --fuente "n=40 vacas; ..."
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

PIPELINE = Path(__file__).resolve().parents[1]
METRICAS_DEFAULT = PIPELINE.parent / "informes" / "campana_20260912" / "metricas.json"
VERSION_DEFAULT = "campana_20260912"
CAMPANA = "campaña de calibración 12 sep 2026"
CLAVES_AJUSTE = ("a", "b", "sigma_log", "t", "n", "factor_ip")
CLAVES_FUENTE = ("mape", "mape_ic95")
N_MIN = 3
# Tolerancia relativa entre factor_ip y exp(t·sigma_log·sqrt(1+1/n)): absorbe el redondeo del evaluador,
# no un factor calculado con otra fórmula.
TOL_FACTOR = 1e-3


def _numero(metricas: dict, clave: str) -> float:
    v = metricas[clave]
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        raise ValueError(f"'{clave}' debe ser un numero finito; se recibio {v!r}")
    return float(v)


def factor_intervalo(sigma_log: float, t: float, n: int) -> float:
    """Factor multiplicativo del IP 95 %: exp(t · sigma_log · sqrt(1 + 1/n))."""
    return math.exp(t * sigma_log * math.sqrt(1.0 + 1.0 / n))


def texto_fuente(n: int, mape: float, ic95: tuple[float, float]) -> str:
    """Procedencia legible del ajuste, tal como la muestra la app en la ficha del modelo."""
    return f"n={n} vacas; {CAMPANA}; MAPE LOO {mape:.2f} % (IC95 {ic95[0]:.1f}–{ic95[1]:.1f})"


def construir_bundle(metricas: dict, version: str = VERSION_DEFAULT, fuente: str | None = None) -> dict:
    """Valida las métricas y devuelve el bundle con las claves en el orden que espera la app.

    Lanza ValueError con el motivo cuando las métricas no sirven para desplegar.
    Sin `fuente`, el texto se construye con n, MAPE LOO e IC95 del propio metricas.json.
    """
    requeridas = CLAVES_AJUSTE + (CLAVES_FUENTE if fuente is None else ())
    faltan = [k for k in requeridas if k not in metricas]
    if faltan:
        raise ValueError(f"faltan claves en metricas.json: {', '.join(faltan)}")

    a, b, sigma_log, t = (_numero(metricas, k) for k in ("a", "b", "sigma_log", "t"))
    for nombre, valor in (("a", a), ("b", b), ("sigma_log", sigma_log), ("t", t)):
        if valor <= 0:
            raise ValueError(f"'{nombre}' debe ser positivo; se recibio {valor}")
    n_f = _numero(metricas, "n")
    if not n_f.is_integer() or n_f < N_MIN:
        raise ValueError(f"'n' debe ser un entero >= {N_MIN} (animales de ajuste); se recibio {metricas['n']!r}")
    n = int(n_f)
    factor = _numero(metricas, "factor_ip")
    esperado = factor_intervalo(sigma_log, t, n)
    if abs(factor - esperado) > TOL_FACTOR * esperado:
        raise ValueError(f"'factor_ip' = {factor} no coincide con exp(t*sigma_log*sqrt(1+1/n)) = {esperado:.6f}")

    if fuente is None:
        mape = _numero(metricas, "mape")
        ic = metricas["mape_ic95"]
        if not (isinstance(ic, (list, tuple)) and len(ic) == 2) or any(
            isinstance(x, bool) or not isinstance(x, (int, float)) for x in ic
        ):
            raise ValueError(f"'mape_ic95' debe ser [lo, hi]; se recibio {ic!r}")
        fuente = texto_fuente(n, mape, (float(ic[0]), float(ic[1])))
    if not version:
        raise ValueError("'version' no puede estar vacia")

    return {
        "a": round(a, 4),
        "b": round(b, 4),
        "interval": {"sigma_log": round(sigma_log, 4), "t": round(t, 3), "n": n, "factor": round(factor, 4)},
        "version": version,
        "fuente": fuente,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--metricas", default=str(METRICAS_DEFAULT), help="metricas.json de eval_weight_campana.py")
    ap.add_argument("--out", required=True, help="ruta del weight_model.json a escribir")
    ap.add_argument("--version", default=VERSION_DEFAULT, help="identificador del ajuste (default: %(default)s)")
    ap.add_argument("--fuente", default=None, help="texto de procedencia; por defecto se arma con n, MAPE LOO e IC95")
    args = ap.parse_args(argv)

    ruta = Path(args.metricas)
    try:
        metricas = json.loads(ruta.read_text(encoding="utf-8"))
        if not isinstance(metricas, dict):
            raise ValueError("el JSON de metricas debe ser un objeto")
        bundle = construir_bundle(metricas, args.version, args.fuente)
    except (OSError, ValueError) as e:  # json.JSONDecodeError es subclase de ValueError
        print(f"make_weight_bundle: {ruta}: {e}", file=sys.stderr)
        return 2

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    texto = json.dumps(bundle, indent=2, ensure_ascii=False) + "\n"
    out.write_text(texto, encoding="utf-8")
    print(texto, end="")
    print(f"-> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
