"""Genera las tablas de la campaña de calibración del 12 sep 2026 a partir de la agrupación de fotos.

Entradas (directorio --grupos-dir):
  bitacora_transcrita.csv  fila,pagina,nombre,arete,foto_bitacora_legible,nota   (40 filas de la tabla de campo)
  grupos.csv               foto,grupo,tipo,...                                    (una fila por foto)
  resumen_grupos.csv       grupo,fila_propuesta,foto_representativa,...           (una fila por carpeta)

Salidas (directorio --out-dir):
  bitacora_campana_20260912.csv  fila,nombre,arete,categoria,peso_lb1,peso_lb2,peso_kg,telefono,notas
                                 (con --pesos: peso_lb1 y peso_kg de la hoja de pesaje, por fila)
  fotos_por_vaca.csv             foto,grupo,fila,nombre,arete,telefono

Entran las fotos con tipo `vaca` o `a25` cuyo grupo tiene fila de bitácora asignada; quedan fuera las fotos de la
tabla (`bitacora`) y los grupos sin fila (fotos sueltas). `arete` se trata como texto para conservar los ceros a la
izquierda. `categoria` y los pesos quedan vacíos hasta recibir los pesos de la finca. El teléfono se deduce del
prefijo de la carpeta del grupo (`vaca_` → Xiaomi 15 Ultra, `a25_` → Galaxy A25).

    .venv/bin/python src/build_campana_csvs.py [--grupos-dir DIR] [--out-dir DIR]
"""
from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Separación por animal (bitacora_transcrita.csv, grupos.csv, resumen_grupos.csv), fuera del repositorio.
GRUPOS_DIR = Path(os.environ["BOVINO_CAMPANA_GRUPOS"]).expanduser() if os.environ.get("BOVINO_CAMPANA_GRUPOS") else None
OUT_DIR = ROOT / "data/field/campana_20260912"

TIPOS_MEDIBLES = {"vaca", "a25"}
TELEFONO_POR_PREFIJO = {"vaca": "xiaomi_15_ultra", "a25": "galaxy_a25"}

CAMPOS_BITACORA = ["fila", "nombre", "arete", "categoria", "peso_lb1", "peso_lb2", "peso_kg", "telefono", "notas"]
CAMPOS_FOTOS = ["foto", "grupo", "fila", "nombre", "arete", "telefono"]


def leer_csv(path: Path) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def escribir_csv(path: Path, campos: list[str], filas: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos, lineterminator="\n")
        w.writeheader()
        for r in filas:
            w.writerow({k: r.get(k, "") for k in campos})


def telefono_de(carpeta: str) -> str:
    prefijo = carpeta.split("_", 1)[0]
    if prefijo not in TELEFONO_POR_PREFIJO:
        raise ValueError(f"carpeta de grupo sin teléfono conocido: {carpeta}")
    return TELEFONO_POR_PREFIJO[prefijo]


def construir(grupos_dir: Path) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    bitacora = leer_csv(grupos_dir / "bitacora_transcrita.csv")
    fotos = leer_csv(grupos_dir / "grupos.csv")
    resumen = leer_csv(grupos_dir / "resumen_grupos.csv")

    por_fila = {r["fila"]: r for r in bitacora}
    if len(por_fila) != len(bitacora):
        raise ValueError("filas repetidas en bitacora_transcrita.csv")

    # El código de grupo de grupos.csv ("01", "a25") se une a la carpeta de resumen_grupos.csv
    # ("vaca_01_065052") a través de la foto representativa, que pertenece a ambos.
    codigo_por_foto = {r["foto"]: r["grupo"] for r in fotos}
    carpeta_por_codigo: dict[str, dict[str, str]] = {}
    for g in resumen:
        codigo = codigo_por_foto[g["foto_representativa"]]
        if codigo in carpeta_por_codigo:
            raise ValueError(f"dos carpetas comparten el código de grupo {codigo}")
        carpeta_por_codigo[codigo] = g

    telefono_por_fila: dict[str, str] = {}
    filas_fotos: list[dict[str, str]] = []
    for r in fotos:
        if r["tipo"] not in TIPOS_MEDIBLES:
            continue
        g = carpeta_por_codigo[r["grupo"]]
        fila = g["fila_propuesta"]
        if not fila:
            continue
        b = por_fila[fila]
        if g["nombre_propuesto"] != b["nombre"]:
            raise ValueError(f"grupo {g['grupo']}: nombre {g['nombre_propuesto']!r} no coincide con la fila {fila}")
        telefono = telefono_de(g["grupo"])
        telefono_por_fila.setdefault(fila, telefono)
        filas_fotos.append({
            "foto": r["foto"], "grupo": g["grupo"], "fila": fila,
            "nombre": b["nombre"], "arete": b["arete"], "telefono": telefono,
        })
    filas_fotos.sort(key=lambda r: (int(r["fila"]), r["foto"]))
    if len({r["foto"] for r in filas_fotos}) != len(filas_fotos):
        raise ValueError("nombres de foto repetidos en fotos_por_vaca")

    filas_bitacora = [{
        "fila": b["fila"], "nombre": b["nombre"], "arete": b["arete"],
        "telefono": telefono_por_fila.get(b["fila"], ""), "notas": b["nota"],
    } for b in sorted(bitacora, key=lambda b: int(b["fila"]))]
    return filas_bitacora, filas_fotos


LB_A_KG = 0.45359237


def incorporar_pesos(bitacora: list[dict[str, str]], pesos_csv: Path) -> None:
    """Copia a la bitácora la lectura de cinta de cada fila (`peso_lb1`, `peso_kg`) y anota fecha e instrumento."""
    pesos = {r["fila"]: r for r in leer_csv(pesos_csv)}
    for b in bitacora:
        r = pesos.get(b["fila"])
        if r is None or not r.get("peso_lb", "").strip():
            continue
        if r["nombre"].strip() != b["nombre"] or r["arete"].strip() != b["arete"]:
            raise ValueError(f"fila {b['fila']}: la hoja de pesaje ({r['nombre']}, {r['arete']}) no coincide con la bitácora")
        lb = float(r["peso_lb"])
        b["peso_lb1"] = r["peso_lb"].strip()
        b["peso_kg"] = f"{lb * LB_A_KG:.3f}"
        nota = f"pesaje {r['fecha_pesaje']}, {r['instrumento']}"
        b["notas"] = f"{b['notas']}; {nota}" if b["notas"] else nota


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Genera bitacora_campana_20260912.csv y fotos_por_vaca.csv.")
    ap.add_argument("--grupos-dir", type=Path, default=GRUPOS_DIR, required=GRUPOS_DIR is None,
                    help="directorio con bitacora_transcrita.csv, grupos.csv y resumen_grupos.csv (o $BOVINO_CAMPANA_GRUPOS)")
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR, help="directorio de salida")
    ap.add_argument("--pesos", type=Path, default=None,
                    help="CSV de la hoja de pesaje (fila, nombre, arete, peso_lb, fecha_pesaje, instrumento) para rellenar peso_lb1 y peso_kg")
    args = ap.parse_args(argv)

    bitacora, fotos = construir(args.grupos_dir.expanduser())
    if args.pesos is not None:
        incorporar_pesos(bitacora, args.pesos.expanduser())
    out_dir = args.out_dir.expanduser()
    escribir_csv(out_dir / "bitacora_campana_20260912.csv", CAMPOS_BITACORA, bitacora)
    escribir_csv(out_dir / "fotos_por_vaca.csv", CAMPOS_FOTOS, fotos)

    por_telefono: dict[str, int] = {}
    for r in fotos:
        por_telefono[r["telefono"]] = por_telefono.get(r["telefono"], 0) + 1
    print(f"bitácora: {len(bitacora)} filas -> {out_dir / 'bitacora_campana_20260912.csv'}")
    print(f"fotos por vaca: {len(fotos)} fotos, {len({r['fila'] for r in fotos})} vacas "
          f"({', '.join(f'{k} {v}' for k, v in sorted(por_telefono.items()))}) -> {out_dir / 'fotos_por_vaca.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
