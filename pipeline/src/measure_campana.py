"""Mide la campaña de calibración del 12 sep 2026: escala, distancia y morfometría por foto.

Para cada foto de `fotos_por_vaca.csv` reutiliza el core del pipeline: `ArucoDetector` (ID 0, DICT_6X6_250) para la
escala, `CowSegmenter` (YOLO26n-seg, vaca de mayor área) para la silueta y `core.morphometry.measure` para las
medidas en cm. Añade la distancia cámara–marcador estimada con la focal EXIF y la corrección de paralaje del área.

Dos pasadas:
  1. mide todas las fotos y escribe `features_campana_20260912.csv` (una fila por foto);
  2. marca `seleccionada_3m` (las 5 fotos `ok` por vaca más cercanas a 3.0 m, desempate por nombre de foto) y guarda
     un overlay de control (silueta + marcador, 1024 px de ancho) solo de esas fotos en `--qa-dir`, fuera del
     repositorio. No se escriben máscaras.

Escala: `marker_px` es la media de los cuatro lados del marcador (misma definición que `eval_aruco_parity.py`);
`px_per_cm = marker_px / lado_cm`. Distancia: `distancia_m = f_px · lado_m / marker_px`, con `f_px = W · f35 / 36` y
`f35` la focal equivalente a 35 mm del EXIF (`FocalLengthIn35mmFilm`); sin EXIF se asume la focal del teléfono por
ancho de imagen (4096 px → 23 mm, 4080 px → 27 mm) y se avisa. Corrección de paralaje: el marcador se sostiene
Δ = 0.50 m delante del plano de la silueta, por lo que `lateral_area_cm2_corr = lateral_area_cm2 · ((d + Δ) / d)²`;
longitudes y alturas quedan crudas.

`estado`: `sin_vaca` > `sin_marcador` > `silueta_cortada` (caja > 0.97·W o > 0.97·H, o pegada al borde izquierdo o
derecho) > `ok`. `nivel_distancia` ∈ {2.5, 3.0, 3.5} es el nivel nominal más cercano (cortes 2.75 y 3.25 m).

    .venv/bin/python src/measure_campana.py [--fotos DIR] [--fotos-por-vaca CSV] [--out CSV] [--modelo PATH]
                                            [--delta 0.50] [--marker-cm 15.0] [--qa-dir DIR] [--limit N]
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from core.aruco import ArucoDetection, ArucoDetector  # noqa: E402
from core.calibration import from_marker  # noqa: E402
from core.morphometry import measure  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data/field/campana_20260912"
# Fotografías originales de la campaña, fuera del repositorio: --fotos o $BOVINO_CAMPANA_RAW.
FOTOS_DIR = Path(os.environ["BOVINO_CAMPANA_RAW"]).expanduser() if os.environ.get("BOVINO_CAMPANA_RAW") else None
# Overlays de control, fuera del repositorio: --qa-dir, $BOVINO_CAMPANA_QA o, por defecto, <fotos>_qa junto a los crudos.
QA_DIR = Path(os.environ["BOVINO_CAMPANA_QA"]).expanduser() if os.environ.get("BOVINO_CAMPANA_QA") else None
MODELO = ROOT / "models/yolo26n-seg.pt"

MARKER_CM = 15.0
DELTA_PARALAJE_M = 0.50
NIVELES_M = (2.5, 3.0, 3.5)
OBJETIVO_M = 3.0
N_SELECCION = 5
ANCHO_QA_PX = 1024
BORDE_CORTE = 0.97
# Focal equivalente a 35 mm por ancho de imagen, para fotos sin EXIF (Xiaomi 15 Ultra y Galaxy A25).
F35_POR_ANCHO = {4096: 23, 4080: 27}
TAG_EXIF_IFD = 0x8769
TAG_F35 = 41989

CAMPOS = ["foto", "fila", "nombre", "arete", "telefono", "marker_px", "px_per_cm", "distancia_m", "nivel_distancia",
          "cow_conf", "area_px", "lateral_area_cm2", "lateral_area_cm2_corr", "body_length_cm", "height_cm",
          "chest_depth_cm", "aspect_ratio", "fill_ratio", "marcador_en_caja", "seleccionada_3m", "estado"]


# ---------------------------------------------------------------- funciones puras (cubiertas por la prueba unitaria)

def focal_px(ancho_px: int, f35_mm: float) -> float:
    """Focal en píxeles a partir de la focal equivalente a 35 mm y el ancho del sensor virtual (36 mm)."""
    return ancho_px * f35_mm / 36.0


def distancia_m(marker_px: float, f_px: float, marker_cm: float = MARKER_CM) -> float:
    """Distancia cámara–marcador por semejanza: lado real / lado en píxeles × focal."""
    return f_px * (marker_cm / 100.0) / marker_px


def nivel_distancia(d_m: float) -> float:
    """Nivel nominal de la campaña más cercano a la distancia medida."""
    return min(NIVELES_M, key=lambda n: abs(n - d_m))


def corregir_area(area_cm2: float, d_m: float, delta_m: float = DELTA_PARALAJE_M) -> float:
    """Área reescalada al plano de la silueta, Δ metros detrás del marcador."""
    return area_cm2 * ((d_m + delta_m) / d_m) ** 2


def silueta_cortada(bbox_xyxy: tuple[int, int, int, int], ancho: int, alto: int) -> bool:
    x0, y0, x1, y1 = bbox_xyxy
    return (x1 - x0) > BORDE_CORTE * ancho or (y1 - y0) > BORDE_CORTE * alto or x0 <= 2 or x1 >= ancho - 3


def clasificar_estado(hay_vaca: bool, hay_marcador: bool, cortada: bool) -> str:
    if not hay_vaca:
        return "sin_vaca"
    if not hay_marcador:
        return "sin_marcador"
    if cortada:
        return "silueta_cortada"
    return "ok"


def seleccionar_3m(filas: list[dict], n: int = N_SELECCION, objetivo_m: float = OBJETIVO_M) -> set[str]:
    """Fotos elegidas por vaca: las `n` con `estado == ok` de menor |distancia − objetivo|, desempate por `foto`."""
    por_vaca: dict[str, list[dict]] = defaultdict(list)
    for r in filas:
        if r.get("estado") == "ok" and r.get("distancia_m") not in (None, ""):
            por_vaca[r["fila"]].append(r)
    elegidas: set[str] = set()
    for candidatas in por_vaca.values():
        candidatas.sort(key=lambda r: (abs(float(r["distancia_m"]) - objetivo_m), r["foto"]))
        elegidas.update(r["foto"] for r in candidatas[:n])
    return elegidas


def lado_medio_px(corners: np.ndarray) -> float:
    c = np.asarray(corners, dtype=float)
    return float(np.mean([np.linalg.norm(c[i] - c[(i + 1) % 4]) for i in range(4)]))


# ---------------------------------------------------------------------------------------------- lectura de imágenes

def f35_exif(path: Path) -> int | None:
    with Image.open(path) as im:
        valor = im.getexif().get_ifd(TAG_EXIF_IFD).get(TAG_F35)
    return int(valor) if valor else None


def leer_fotos_por_vaca(path: Path, limit: int | None) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as f:
        filas = list(csv.DictReader(f))
    return filas[:limit] if limit else filas


# ------------------------------------------------------------------------------------------------- medición por foto

def medir(img: np.ndarray, f35: int | None, aruco: ArucoDetector, seg, marker_cm: float, delta_m: float) -> tuple[dict, dict]:
    """Mide una foto. Devuelve (columnas del CSV, material para el overlay de control)."""
    alto, ancho = img.shape[:2]
    dets = aruco.detect(img)
    marcador = max(dets, key=lambda d: lado_medio_px(d.corners)) if dets else None
    vaca = seg.largest(seg.segment(img))

    fila: dict = {}
    calib = None
    d_m = None
    if marcador is not None:
        marker_px = lado_medio_px(marcador.corners)
        calib = from_marker(marker_px, marker_cm)
        fila["marker_px"] = round(marker_px, 2)
        fila["px_per_cm"] = round(calib.px_per_cm, 4)
        if f35 is not None:
            d_m = distancia_m(marker_px, focal_px(ancho, f35), marker_cm)
            fila["distancia_m"] = round(d_m, 3)
            fila["nivel_distancia"] = f"{nivel_distancia(d_m):.1f}"

    cortada = False
    if vaca is not None:
        fila["cow_conf"] = round(vaca.confidence, 3)
        fila["area_px"] = vaca.area_px
        cortada = silueta_cortada(vaca.bbox_xyxy, ancho, alto)
        if calib is not None:
            mo = measure(vaca.mask, calib)
            fila.update(mo.as_features())
            if d_m is not None:
                fila["lateral_area_cm2_corr"] = round(corregir_area(mo.lateral_area_cm2, d_m, delta_m), 2)
            cx, cy = marcador.center
            x0, y0, x1, y1 = vaca.bbox_xyxy
            fila["marcador_en_caja"] = int(x0 <= cx <= x1 and y0 <= cy <= y1)

    fila["estado"] = clasificar_estado(vaca is not None, marcador is not None, cortada)

    qa: dict = {}
    if fila["estado"] == "ok":
        escala = ANCHO_QA_PX / ancho
        alto_qa = round(alto * escala)
        mascara_qa = cv2.resize(vaca.mask, (ANCHO_QA_PX, alto_qa), interpolation=cv2.INTER_NEAREST)
        ok, png = cv2.imencode(".png", mascara_qa * 255)
        if not ok:
            raise RuntimeError("no se pudo codificar la máscara reducida")
        qa = {"mascara_png": png.tobytes(), "corners": marcador.corners * escala, "conf": vaca.confidence}
    return fila, qa


def escribir_overlay(path_foto: Path, fila: dict, qa: dict, destino: Path) -> None:
    from core.segmenter import CowSegmentation, CowSegmenter  # import diferido: solo se usa con el modelo cargado

    img = cv2.imread(str(path_foto))
    alto, ancho = img.shape[:2]
    escala = ANCHO_QA_PX / ancho
    reducida = cv2.resize(img, (ANCHO_QA_PX, round(alto * escala)), interpolation=cv2.INTER_AREA)
    mascara = cv2.imdecode(np.frombuffer(qa["mascara_png"], dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
    ys, xs = np.where(mascara > 0)
    caja = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))
    ov = CowSegmenter.overlay(reducida, CowSegmentation(qa["conf"], caja, (mascara > 0).astype(np.uint8)))
    corners = np.asarray(qa["corners"], dtype=np.float32)
    marcador = ArucoDetection(0, corners, tuple(corners.mean(axis=0).tolist()), lado_medio_px(corners))
    ov = ArucoDetector.draw(ov, [marcador])
    texto = (f"fila {int(fila['fila']):02d} {fila['nombre']} | d={fila['distancia_m']:.2f} m ({fila['nivel_distancia']}) | "
             f"A={fila['lateral_area_cm2']:.0f} cm2 corr={fila['lateral_area_cm2_corr']:.0f} | "
             f"L={fila['body_length_cm']:.0f} H={fila['height_cm']:.0f}")
    cv2.putText(ov, texto, (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 3)
    cv2.putText(ov, texto, (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    destino.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(destino), ov, [cv2.IMWRITE_JPEG_QUALITY, 85])


# ------------------------------------------------------------------------------------------------------------ resumen

def percentiles(valores: list[float], ps: tuple[float, ...]) -> str:
    if not valores:
        return "sin datos"
    return " / ".join(f"{np.percentile(valores, p):.1f}" for p in ps)


def resumen(filas: list[dict], out_csv: Path, qa_dir: Path, segundos: float) -> None:
    n = len(filas)
    con_marcador = sum(1 for r in filas if r.get("marker_px") not in (None, ""))
    con_vaca = sum(1 for r in filas if r.get("cow_conf") not in (None, ""))
    estados = Counter(r["estado"] for r in filas)
    niveles = Counter(r["nivel_distancia"] for r in filas if r.get("nivel_distancia"))
    ok = [r for r in filas if r["estado"] == "ok"]
    sel_por_vaca = Counter(r["fila"] for r in filas if r.get("seleccionada_3m") == 1)
    vacas = sorted({r["fila"] for r in filas}, key=int)
    con_cinco = [v for v in vacas if sel_por_vaca[v] >= N_SELECCION]
    con_menos = [v for v in vacas if sel_por_vaca[v] < N_SELECCION]

    print(f"\nfotos: {n}")
    print(f"marcador decodificado: {con_marcador}/{n}")
    print(f"vaca segmentada: {con_vaca}/{n}")
    print("estado: " + ", ".join(f"{k} {estados[k]}" for k in ("ok", "sin_vaca", "sin_marcador", "silueta_cortada")))
    print("nivel_distancia (fotos con marcador): " + ", ".join(f"{k} m {niveles[k]}" for k in sorted(niveles)))
    print(f"height_cm (ok) p5 / p50 / p95: {percentiles([r['height_cm'] for r in ok], (5, 50, 95))}")
    print(f"body_length_cm (ok) p2.5 / p50 / p97.5: {percentiles([r['body_length_cm'] for r in ok], (2.5, 50, 97.5))}")
    print(f"seleccionada_3m: {sum(sel_por_vaca.values())} fotos; vacas con {N_SELECCION}: {len(con_cinco)}; con menos: {len(con_menos)}"
          + (" (" + ", ".join(f"fila {v}: {sel_por_vaca[v]}" for v in con_menos) + ")" if con_menos else ""))
    print(f"tiempo: {segundos / 60:.1f} min ({segundos / max(n, 1):.2f} s/foto)")
    print(f"-> {out_csv}")
    print(f"-> overlays de control en {qa_dir}")


# --------------------------------------------------------------------------------------------------------------- main

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Mide las fotos de la campaña de calibración (escala, distancia, morfometría).")
    ap.add_argument("--fotos", type=Path, default=FOTOS_DIR, required=FOTOS_DIR is None, help="directorio con las fotos originales (o $BOVINO_CAMPANA_RAW)")
    ap.add_argument("--fotos-por-vaca", type=Path, default=DATA_DIR / "fotos_por_vaca.csv", help="CSV foto → vaca")
    ap.add_argument("--out", type=Path, default=DATA_DIR / "features_campana_20260912.csv", help="CSV de salida")
    ap.add_argument("--modelo", type=Path, default=MODELO, help="pesos YOLO26n-seg")
    ap.add_argument("--delta", type=float, default=DELTA_PARALAJE_M, help="Δ de paralaje marcador–silueta (m)")
    ap.add_argument("--marker-cm", type=float, default=MARKER_CM, help="lado real del marcador impreso (cm)")
    ap.add_argument("--qa-dir", type=Path, default=QA_DIR, help="directorio de overlays de control, fuera del repositorio (o $BOVINO_CAMPANA_QA; por defecto <fotos>_qa)")
    ap.add_argument("--limit", type=int, default=None, help="medir solo las primeras N fotos")
    args = ap.parse_args(argv)

    from core.segmenter import CowSegmenter  # import diferido: la prueba unitaria no necesita ultralytics

    fotos_dir = args.fotos.expanduser()
    qa_dir = (args.qa_dir or fotos_dir.with_name(fotos_dir.name + "_qa")).expanduser()
    entradas = leer_fotos_por_vaca(args.fotos_por_vaca.expanduser(), args.limit)
    faltan = [r["foto"] for r in entradas if not (fotos_dir / r["foto"]).is_file()]
    if faltan:
        print(f"faltan {len(faltan)} fotos en {fotos_dir}: {', '.join(faltan[:5])}", file=sys.stderr)
        return 1

    aruco = ArucoDetector("DICT_6X6_250", allowed_ids=[0], min_marker_size_px=20)
    seg = CowSegmenter(str(args.modelo), cow_class_id=19, min_confidence=0.5)

    inicio = time.perf_counter()
    filas: list[dict] = []
    material_qa: dict[str, dict] = {}
    n = len(entradas)
    print(f"{'#':>4}/{n} {'foto':28} {'fila':>4} {'nombre':12} {'d_m':>6} {'niv':>4} {'L_cm':>6} {'H_cm':>6} estado", flush=True)
    for i, e in enumerate(entradas, 1):
        path = fotos_dir / e["foto"]
        img = cv2.imread(str(path))
        if img is None:
            print(f"no se pudo leer {path}", file=sys.stderr)
            return 1
        f35 = f35_exif(path)
        if f35 is None:
            f35 = F35_POR_ANCHO.get(img.shape[1])
            print(f"aviso: {e['foto']} sin FocalLengthIn35mmFilm en EXIF; se asume f35 = {f35} por ancho {img.shape[1]} px", flush=True)
        medida, qa = medir(img, f35, aruco, seg, args.marker_cm, args.delta)
        fila = {k: e[k] for k in ("foto", "fila", "nombre", "arete", "telefono")}
        fila.update(medida)
        fila["seleccionada_3m"] = 0
        filas.append(fila)
        if qa:
            material_qa[fila["foto"]] = qa
        d = fila.get("distancia_m")
        print(f"{i:>4}/{n} {fila['foto']:28} {fila['fila']:>4} {fila['nombre']:12} "
              f"{(f'{d:.3f}' if d is not None else '-'):>6} {fila.get('nivel_distancia', '-'):>4} "
              f"{(f'{fila['body_length_cm']:.1f}' if 'body_length_cm' in fila else '-'):>6} "
              f"{(f'{fila['height_cm']:.1f}' if 'height_cm' in fila else '-'):>6} {fila['estado']}", flush=True)

    elegidas = seleccionar_3m(filas)
    for fila in filas:
        fila["seleccionada_3m"] = int(fila["foto"] in elegidas)

    out_csv = args.out.expanduser()
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS, lineterminator="\n")
        w.writeheader()
        for fila in filas:
            w.writerow({k: fila.get(k, "") for k in CAMPOS})

    for fila in filas:
        if fila["seleccionada_3m"]:
            destino = qa_dir / f"{int(fila['fila']):02d}_{fila['nombre']}_{Path(fila['foto']).stem}.jpg"
            escribir_overlay(fotos_dir / fila["foto"], fila, material_qa[fila["foto"]], destino)

    resumen(filas, out_csv, qa_dir, time.perf_counter() - inicio)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
