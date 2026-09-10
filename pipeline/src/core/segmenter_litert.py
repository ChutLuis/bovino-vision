"""Segmentador que reproduce en PC la ruta del APK: LiteRT + postproceso de app/src/vision.

Copia paso a paso `app/src/vision/image.ts` (letterbox bilineal a 640×640 NCHW, relleno 114/255)
y `app/src/vision/segment.ts` (filtro por confianza y clase, máscara = Σ coef·prototipo > 0
recortada a la caja en la rejilla 160×160 y remuestreada al tamaño original por vecino más
cercano). Sirve para validar en PC lo que el teléfono calcularía con el mismo .tflite.

Diferencia conocida e inevitable: el APK decodifica JPEG con jpeg-js y aquí se usa libjpeg (cv2);
los píxeles pueden diferir en ±1 nivel. Todo lo demás es idéntico por construcción.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import cv2
import numpy as np

INPUT_SIZE = 640
MASK_SIZE = 160
MASK_CHANNELS = 32
DETECTION_ROWS = 300
DETECTION_ROW_SIZE = 38
PAD_VALUE = 114 / 255


def js_round(x: float) -> int:
    """Math.round de JavaScript para valores no negativos (redondea .5 hacia arriba)."""
    return int(math.floor(x + 0.5))


@dataclass
class Letterbox:
    original_width: int
    original_height: int
    scale: float
    content_width: int
    content_height: int
    pad_x: int
    pad_y: int


def letterbox_nchw(rgb: np.ndarray, size: int = INPUT_SIZE) -> tuple[np.ndarray, Letterbox]:
    """Equivalente vectorizado de letterboxToNchw (image.ts): bilineal con centros de píxel."""
    h, w = rgb.shape[:2]
    scale = min(size / w, size / h)
    cw, ch = js_round(w * scale), js_round(h * scale)
    px, py = (size - cw) // 2, (size - ch) // 2

    xs = np.arange(cw, dtype=np.float64)
    sx = np.clip((xs + 0.5) / scale - 0.5, 0, w - 1)
    x0 = np.floor(sx).astype(int)
    x1 = np.minimum(w - 1, x0 + 1)
    wx = (sx - x0).astype(np.float32)
    ys = np.arange(ch, dtype=np.float64)
    sy = np.clip((ys + 0.5) / scale - 0.5, 0, h - 1)
    y0 = np.floor(sy).astype(int)
    y1 = np.minimum(h - 1, y0 + 1)
    wy = (sy - y0).astype(np.float32)

    img = rgb.astype(np.float32)
    top = img[y0][:, x0] * (1 - wx)[None, :, None] + img[y0][:, x1] * wx[None, :, None]
    bottom = img[y1][:, x0] * (1 - wx)[None, :, None] + img[y1][:, x1] * wx[None, :, None]
    content = (top * (1 - wy)[:, None, None] + bottom * wy[:, None, None]) / 255.0

    inp = np.full((3, size, size), PAD_VALUE, dtype=np.float32)
    inp[:, py:py + ch, px:px + cw] = content.transpose(2, 0, 1)
    return inp, Letterbox(w, h, scale, cw, ch, px, py)


def prototype_index_maps(lb: Letterbox, size: int = INPUT_SIZE, msize: int = MASK_SIZE) -> tuple[np.ndarray, np.ndarray]:
    """Para cada píxel original, la celda 160×160 que le corresponde (segment.ts: crop del letterbox + nearest)."""
    xs = np.arange(lb.original_width)
    x640 = lb.pad_x + np.minimum(lb.content_width - 1, (xs * lb.content_width) // lb.original_width)
    px = np.minimum(msize - 1, (x640 * msize) // size)
    ys = np.arange(lb.original_height)
    y640 = lb.pad_y + np.minimum(lb.content_height - 1, (ys * lb.content_height) // lb.original_height)
    py = np.minimum(msize - 1, (y640 * msize) // size)
    return px.astype(int), py.astype(int)


def mask_from_row(row: np.ndarray, protos: np.ndarray, lb: Letterbox,
                  size: int = INPUT_SIZE, msize: int = MASK_SIZE) -> np.ndarray:
    """Máscara binaria en píxeles originales para una fila de detección [x1,y1,x2,y2,conf,cls,32 coef]."""
    coeffs = row[6:6 + MASK_CHANNELS].astype(np.float32)
    logits = np.tensordot(coeffs, protos.astype(np.float32), axes=(0, 0))  # (160, 160)
    x0 = max(0, math.floor(row[0] * msize / size))
    y0 = max(0, math.floor(row[1] * msize / size))
    x1 = min(msize, math.ceil(row[2] * msize / size))
    y1 = min(msize, math.ceil(row[3] * msize / size))
    px, py = prototype_index_maps(lb, size, msize)
    inside = logits[py[:, None], px[None, :]] > 0
    rows_ok = (py >= y0) & (py < y1)
    cols_ok = (px >= x0) & (px < x1)
    return (inside & rows_ok[:, None] & cols_ok[None, :]).astype(np.uint8)


def box_in_original(row: np.ndarray, lb: Letterbox) -> tuple[float, float, float, float]:
    def ox(v):
        return round_px(min(lb.original_width, max(0.0, (v - lb.pad_x) / lb.scale)))

    def oy(v):
        return round_px(min(lb.original_height, max(0.0, (v - lb.pad_y) / lb.scale)))

    return ox(row[0]), oy(row[1]), ox(row[2]), oy(row[3])


def round_px(v: float) -> float:
    return math.floor(v * 100 + 0.5) / 100


@dataclass
class LiteRTDetection:
    confidence: float
    class_id: int
    bbox_original: tuple[float, float, float, float]
    mask: np.ndarray

    @property
    def area_px(self) -> int:
        return int(self.mask.sum())


class LiteRTCowSegmenter:
    """Misma interfaz que core.segmenter.CowSegmenter.segment(); devuelve objetos con .mask/.area_px/.confidence/.bbox_xyxy."""

    def __init__(self, model_path: str, cow_class_id: int = 19, min_confidence: float = 0.5,
                 device: str = "", num_threads: int = 4) -> None:
        from ai_edge_litert.interpreter import Interpreter
        self._it = Interpreter(model_path=str(model_path), num_threads=num_threads)
        self._it.allocate_tensors()
        inp = self._it.get_input_details()[0]
        if inp["shape"].tolist() != [1, 3, INPUT_SIZE, INPUT_SIZE]:
            raise ValueError(f"entrada inesperada {inp['shape'].tolist()}, se esperaba [1,3,640,640]")
        self._in_idx = inp["index"]
        outs = self._it.get_output_details()
        self._det_idx = next(d["index"] for d in outs if d["shape"].tolist() == [1, DETECTION_ROWS, DETECTION_ROW_SIZE])
        self._proto_idx = next(d["index"] for d in outs if d["shape"].tolist() == [1, MASK_CHANNELS, MASK_SIZE, MASK_SIZE])
        self._cow = cow_class_id
        self._thr = min_confidence
        self.last_letterbox: Letterbox | None = None

    def run(self, frame_bgr: np.ndarray) -> tuple[np.ndarray, np.ndarray, Letterbox]:
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        inp, lb = letterbox_nchw(rgb)
        self._it.set_tensor(self._in_idx, inp[None])
        self._it.invoke()
        dets = self._it.get_tensor(self._det_idx)[0].astype(np.float32)
        protos = self._it.get_tensor(self._proto_idx)[0].astype(np.float32)
        self.last_letterbox = lb
        return dets, protos, lb

    def detections(self, frame_bgr: np.ndarray) -> list[LiteRTDetection]:
        dets, protos, lb = self.run(frame_bgr)
        out = []
        for row in dets:
            conf = float(row[4])
            cls = js_round(float(row[5])) if np.isfinite(row[5]) else -1
            if not np.isfinite(conf) or conf < self._thr or cls != self._cow:
                continue
            out.append(LiteRTDetection(conf, cls, box_in_original(row, lb), mask_from_row(row, protos, lb)))
        return out

    def segment(self, frame_bgr: np.ndarray):
        from core.segmenter import CowSegmentation
        res = []
        for d in self.detections(frame_bgr):
            x1, y1, x2, y2 = d.bbox_original
            res.append(CowSegmentation(confidence=d.confidence, bbox_xyxy=(int(x1), int(y1), int(x2), int(y2)), mask=d.mask))
        return res
