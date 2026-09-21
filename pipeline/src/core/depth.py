"""Profundidad corporal proyectada de la banda central, en centímetros, sobre la máscara de la app.

Espejo en Python de `app/src/vision/depth.ts`. Entrada: la máscara binaria de la vaca seleccionada en
píxeles originales (la que produce `core.segmenter_litert.mask_from_row`, reconstrucción por vecino más
cercano desde la rejilla 160×160 dentro de la caja) y la escala `cm_per_px` del marcador.

Pasos, en este orden:

1. mayor componente conexo con vecindad de 8, recortado a su caja;
2. apertura horizontal con kernel ``k×1``, ``k = max(3, round(40 / cm_per_px)) | 1``, fondo 0;
3. masa por columna, soporte al 25 % de la mediana de las masas positivas, banda central 25–75 %;
4. mayor corrida vertical de unos por columna;
5. ``D_media`` = media de esas corridas en la banda central × ``cm_per_px``, ceros incluidos.

El redondeo del kernel es media hacia arriba (``floor(x + 0.5)``), no el de `round` de Python, que
redondea los empates al par: así las dos implementaciones no pueden separarse en un ``.5`` exacto.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import cv2
import numpy as np

# Apertura: descarta apéndices más finos que 40 cm (patas, cola, orejas) sin tocar el tronco.
APERTURA_CM = 40.0
# Una columna entra al soporte si su masa llega al 25 % de la mediana de las masas positivas.
FRACCION_SOPORTE = 0.25


def kernel_apertura(cm_per_px: float) -> int:
    """Ancho impar del kernel de apertura, nunca menor que 3."""
    if not math.isfinite(cm_per_px) or cm_per_px <= 0:
        raise ValueError("la escala en centímetros por píxel debe ser positiva")
    return max(3, math.floor(APERTURA_CM / cm_per_px + 0.5)) | 1


def mayor_componente(mask: np.ndarray) -> np.ndarray | None:
    """Mayor componente conexo con vecindad de 8, recortado a su propia caja."""
    mask = (np.asarray(mask) > 0).astype(np.uint8)
    ys, xs = np.nonzero(mask)
    if not len(ys):
        return None
    roi = np.ascontiguousarray(mask[ys.min():ys.max() + 1, xs.min():xs.max() + 1])
    _, labels, stats, _ = cv2.connectedComponentsWithStats(roi, connectivity=8)
    biggest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    comp = (labels == biggest).astype(np.uint8)
    ys, xs = np.nonzero(comp)
    return np.ascontiguousarray(comp[ys.min():ys.max() + 1, xs.min():xs.max() + 1])


def abrir_horizontal(comp: np.ndarray, k: int) -> np.ndarray:
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (k, 1))
    return cv2.morphologyEx(comp, cv2.MORPH_OPEN, kernel,
                            borderType=cv2.BORDER_CONSTANT, borderValue=0)


def corridas_verticales(binaria: np.ndarray) -> np.ndarray:
    """Mayor corrida vertical de unos por columna."""
    run = np.zeros(binaria.shape[1], np.int64)
    best = np.zeros_like(run)
    for row in binaria:
        run = np.where(row > 0, run + 1, 0)
        best = np.maximum(best, run)
    return best


@dataclass(frozen=True)
class Profundidad:
    status: str
    d_media_cm: float | None = None
    d_max_cm: float | None = None
    l_gate_cm: float | None = None
    kernel_px: int | None = None
    lo: int | None = None
    hi: int | None = None
    c0: int | None = None
    c1: int | None = None
    ancho_componente_px: int | None = None

    @property
    def ok(self) -> bool:
        return self.status == "ok"


def profundidad_media(mask: np.ndarray, cm_per_px: float) -> Profundidad:
    """``D_media`` y su geometría, o el estado que explica por qué no se pudo medir."""
    if not math.isfinite(cm_per_px) or cm_per_px <= 0:
        raise ValueError("la escala en centímetros por píxel debe ser positiva")

    comp = mayor_componente(mask)
    if comp is None:
        return Profundidad("mascara_vacia")

    k = kernel_apertura(cm_per_px)
    opened = abrir_horizontal(comp, k)
    mass = opened.sum(axis=0)
    if not mass.any():
        return Profundidad("apertura_vacia")

    med = float(np.median(mass[mass > 0]))
    support = np.nonzero(mass >= FRACCION_SOPORTE * med)[0]
    if not len(support):
        return Profundidad("apertura_vacia")

    lo, hi = int(support.min()), int(support.max()) + 1
    length = hi - lo
    c0, c1 = lo + int(length * 0.25), lo + int(length * 0.75)
    if c1 <= c0:
        return Profundidad("region_vacia")

    runs = corridas_verticales(opened)
    central = runs[c0:c1]
    # La media incluye las columnas en cero: una silueta interrumpida baja la profundidad, no se ignora.
    if not len(central) or central.mean() <= 0:
        return Profundidad("region_vacia")

    return Profundidad(
        "ok",
        d_media_cm=float(central.mean() * cm_per_px),
        d_max_cm=float(central.max() * cm_per_px),
        l_gate_cm=float(length * cm_per_px),
        kernel_px=k,
        lo=lo,
        hi=hi,
        c0=c0,
        c1=c1,
        ancho_componente_px=int(comp.shape[1]),
    )
