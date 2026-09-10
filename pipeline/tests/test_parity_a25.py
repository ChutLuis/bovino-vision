"""La emulación de la ruta del APK en PC (core/segmenter_litert.py) reproduce lo que midió el Galaxy A25.

Referencia: informes/benchmark_a25_20260826_fullres.json (10 fotos, fp32, conf 0.5, clase 19).
Tolerancias: mismo número de detecciones; área ±0.5 % (la única diferencia esperada es el decodificador
JPEG: jpeg-js en el teléfono, libjpeg aquí); confianza ±0.01; caja ±2 px.
"""
import json
from pathlib import Path

import cv2
import pytest

ROOT = Path(__file__).resolve().parent.parent
JSON = ROOT.parent / "informes/benchmark_a25_20260826_fullres.json"
PHOTOS = ROOT.parent / "app-benchmark/assets/photos"
TFLITE = ROOT.parent / "app/assets/model_bundle/yolo26n-seg.tflite"


@pytest.mark.slow
def test_pc_emulation_matches_a25_device():
    pytest.importorskip("ai_edge_litert")
    if not (JSON.exists() and PHOTOS.exists() and TFLITE.exists()):
        pytest.skip("faltan el JSON del benchmark, las fotos o el .tflite del APK")
    from core.segmenter_litert import LiteRTCowSegmenter
    lite = LiteRTCowSegmenter(str(TFLITE), cow_class_id=19, min_confidence=0.5)
    device = [s for s in json.load(open(JSON))["segmentation"] if s["modelo"] == "fp32"]
    assert len(device) == 10
    for dev in device:
        img = cv2.imread(str(PHOTOS / f"photo_{dev['foto']}.jpeg"))
        dets = lite.detections(img)
        assert len(dets) == dev["cow_dets"], dev["foto"]
        sel = max(dets, key=lambda d: d.area_px)
        dif_area = (sel.area_px - dev["mask_area_px"]) / dev["mask_area_px"] * 100
        assert abs(dif_area) <= 0.5, f"{dev['foto']}: área PC {sel.area_px} vs A25 {dev['mask_area_px']} ({dif_area:+.2f} %)"
        assert abs(sel.confidence - dev["selected_confidence"]) <= 0.01, dev["foto"]
        assert max(abs(a - b) for a, b in zip(sel.bbox_original, dev["selected_bbox_original_px"])) <= 2.0, dev["foto"]
