"""CowSegmenter debe recortar el relleno del letterbox antes de escalar la máscara.

Regresión del bug encontrado el 9 sep 2026: r.masks.data está a la resolución de entrada de la red
(384×640 para una foto 4096×2304) y redimensionarlo directo a la imagen aplastaba la silueta un 6 %
en vertical. Referencia: retina_masks=True (máscara nativa a resolución original) y el APK.
"""
from pathlib import Path

import cv2
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
PT = ROOT / "models/yolo26n-seg.pt"


def iou(a, b):
    u = np.logical_or(a, b).sum()
    return float(np.logical_and(a, b).sum() / u) if u else 0.0


@pytest.mark.slow
@pytest.mark.parametrize("qid", ["burst_ambar_01", "burst_taty_01", "5_06_perla"])
def test_mask_matches_retina_masks_reference(qid):
    if not PT.exists():
        pytest.skip("sin models/yolo26n-seg.pt")
    ip = next((ROOT / "data/val_clean/images").glob(f"{qid}.*"), None)
    if ip is None:
        pytest.skip("sin data/val_clean")
    from ultralytics import YOLO
    from core.segmenter import CowSegmenter
    im = cv2.imread(str(ip))
    got = max(CowSegmenter(str(PT), 19, 0.5, device="cpu").segment(im), key=lambda c: c.area_px).mask
    rr = YOLO(str(PT)).predict(source=im, classes=[19], conf=0.5, verbose=False, device="cpu", retina_masks=True)[0]
    ref = max(((m.cpu().numpy() > 0.5).astype(np.uint8) for m in rr.masks.data), key=lambda m: int(m.sum()))
    assert got.shape == ref.shape == im.shape[:2]
    assert iou(got, ref) > 0.97, f"{qid}: IoU {iou(got, ref):.3f} contra retina_masks (¿relleno sin recortar?)"
    rows_got = np.where(got.any(axis=1))[0]
    rows_ref = np.where(ref.any(axis=1))[0]
    assert abs(int(rows_got.min()) - int(rows_ref.min())) <= 8 and abs(int(rows_got.max()) - int(rows_ref.max())) <= 8
