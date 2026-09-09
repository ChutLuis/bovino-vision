"""Funciones puras para evaluar segmentación de instancias contra máscaras de referencia.

No importa ultralytics: sirve para pruebas unitarias rápidas y para el script
`eval_finetuned_iou.py`, que es quien corre los modelos.

Convenciones:
- Una máscara es un `np.ndarray` uint8/bool de HxW con 1 en la vaca.
- `gts[0]` es la vaca objetivo (la que se pesó). En `data/val_clean` es `inst0`.
- La "máscara elegida" es la de mayor área, igual que hace el pipeline de peso
  (`CowSegmenter.largest`).
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path

import cv2
import numpy as np


def iou(a: np.ndarray, b: np.ndarray) -> float:
    union = np.logical_or(a, b).sum()
    return float(np.logical_and(a, b).sum() / union) if union else 0.0


def parse_label_lines(text: str) -> list[np.ndarray]:
    """Etiqueta YOLO-seg -> lista de polígonos normalizados (N_i x 2), UNA POR LÍNEA.

    Cada línea es `cls x1 y1 x2 y2 ...`. Leer el archivo entero de una vez mezcla los
    ids de clase con las coordenadas (bug histórico de eval_finetuned_iou.py).
    """
    polys = []
    for line in text.splitlines():
        toks = line.split()
        if len(toks) < 7:  # cls + al menos 3 puntos
            continue
        pts = np.array(toks[1:], dtype=float)
        if len(pts) % 2:
            raise ValueError(f"línea con número impar de coordenadas: {line[:60]}...")
        polys.append(pts.reshape(-1, 2))
    return polys


def rasterize(poly_norm: np.ndarray, w: int, h: int) -> np.ndarray:
    pts = poly_norm.copy()
    pts[:, 0] *= w
    pts[:, 1] *= h
    m = np.zeros((h, w), np.uint8)
    cv2.fillPoly(m, [pts.astype(np.int32)], 1)
    return m


def load_gt_polygons(label_path: Path, w: int, h: int) -> list[np.ndarray]:
    return [rasterize(p, w, h) for p in parse_label_lines(label_path.read_text())]


def load_gt_pngs(masks_dir: Path, qid: str, w: int, h: int) -> list[np.ndarray]:
    """PNG `{qid}_inst{k}.png` ordenados por k; se remuestrean a WxH si hace falta."""
    paths = sorted(masks_dir.glob(f"{qid}_inst*.png"), key=lambda p: int(p.stem.rsplit("inst", 1)[1]))
    out = []
    for p in paths:
        m = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
        if m is None:
            continue
        if m.shape[:2] != (h, w):
            m = cv2.resize(m, (w, h), interpolation=cv2.INTER_NEAREST)
        out.append((m > 127).astype(np.uint8))
    return out


def greedy_match(preds: list[np.ndarray], gts: list[np.ndarray]) -> tuple[np.ndarray, list[float]]:
    """Empareja predicciones con GT tomando cada vez el par de mayor IoU.

    Devuelve la matriz IoU (preds x gts) y el IoU emparejado por GT (0 si no hay pareja).
    """
    if not gts:
        return np.zeros((len(preds), 0)), []
    M = np.array([[iou(p, g) for g in gts] for p in preds]) if preds else np.zeros((0, len(gts)))
    matched = [0.0] * len(gts)
    if M.size == 0:
        return M, matched
    work = M.copy()
    for _ in range(min(len(preds), len(gts))):
        i, j = np.unravel_index(np.argmax(work), work.shape)
        if work[i, j] <= 0:
            break
        matched[j] = float(work[i, j])
        work[i, :] = -1
        work[:, j] = -1
    return M, matched


@dataclass
class ImageEval:
    n_gt: int
    n_pred: int
    sin_deteccion: bool
    eligio_objetivo: bool
    iou_objetivo: float
    err_area_objetivo: float
    iou_emparejado_medio: float
    recall_inst_050: float
    fp: int

    def as_row(self) -> dict:
        d = asdict(self)
        for k in ("iou_objetivo", "err_area_objetivo", "iou_emparejado_medio", "recall_inst_050"):
            d[k] = round(d[k], 4)
        return d


def evaluate_image(preds: list[np.ndarray], gts: list[np.ndarray], target: int = 0, thr: float = 0.5) -> ImageEval:
    """Métricas de una imagen. `gts[target]` es la vaca objetivo."""
    if not gts:
        raise ValueError("sin máscaras de referencia")
    if not preds:
        return ImageEval(len(gts), 0, True, False, 0.0, -1.0, 0.0, 0.0, 0)
    sel = int(np.argmax([int(m.sum()) for m in preds]))
    M, matched = greedy_match(preds, gts)
    iou_t = float(M[sel, target])
    eligio = iou_t >= thr and iou_t >= float(M[sel].max())
    err = (int(preds[sel].sum()) - int(gts[target].sum())) / int(gts[target].sum())
    recall = float(np.mean([m >= thr for m in matched]))
    fp = int((M.max(axis=1) < thr).sum())
    return ImageEval(len(gts), len(preds), False, bool(eligio), iou_t, float(err),
                     float(np.mean(matched)), recall, fp)


def bootstrap_paired_by_group(values_a: dict[str, list[float]], values_b: dict[str, list[float]],
                              n_boot: int = 5000, seed: int = 0) -> dict:
    """IC95 bootstrap de la diferencia media (b - a), remuestreando GRUPOS (animales).

    `values_x[grupo]` = lista de valores por imagen de ese grupo. Primero se promedia por
    grupo, luego se remuestrean los grupos con reemplazo.
    """
    groups = sorted(set(values_a) & set(values_b))
    diffs = np.array([np.mean(values_b[g]) - np.mean(values_a[g]) for g in groups])
    rng = np.random.default_rng(seed)
    boots = np.array([rng.choice(diffs, len(diffs), replace=True).mean() for _ in range(n_boot)])
    return {
        "n_grupos": len(groups),
        "dif_media": round(float(diffs.mean()), 4),
        "ic95": [round(float(np.percentile(boots, 2.5)), 4), round(float(np.percentile(boots, 97.5)), 4)],
        "por_grupo": {g: round(float(d), 4) for g, d in zip(groups, diffs)},
    }
