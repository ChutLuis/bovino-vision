"""Contrato del modelo LiteRT que consume el APK, su manifiesto y reproducibilidad de la exportación."""
import hashlib
import json
import re
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PT = ROOT / "models/yolo26n-seg.pt"
APK_TFLITE = ROOT.parent / "app/assets/model_bundle/yolo26n-seg.tflite"
MANIFEST = APK_TFLITE.parent / "model_manifest.json"
CONFIG_TS = ROOT.parent / "app/src/vision/config.ts"

INPUT = [1, 3, 640, 640]
OUT0 = [1, 300, 38]      # 300 detecciones x (4 caja + 1 conf + 1 clase + 32 coeficientes)
OUT1 = [1, 32, 160, 160]  # prototipos de máscara


def body(b: bytes) -> bytes:
    """Bytes del modelo sin el zip de metadatos que Ultralytics anexa (empieza en PK\\x03\\x04)."""
    i = b.find(b"PK\x03\x04")
    return b if i < 0 else b[:i]


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_manifest_matches_apk_model():
    """model_manifest.json describe exactamente el .tflite que va en el APK (make_model_manifest.py)."""
    if not APK_TFLITE.exists():
        pytest.skip("sin app/assets/model_bundle/yolo26n-seg.tflite")
    m = json.loads(MANIFEST.read_text())
    raw = APK_TFLITE.read_bytes()
    assert m["model_file"] == APK_TFLITE.name
    assert m["sha256"] == hashlib.sha256(raw).hexdigest(), "el sha256 del manifiesto no es el del .tflite: corre make_model_manifest.py"
    assert m["body_sha256"] == hashlib.sha256(body(raw)).hexdigest()
    assert m["size_bytes"] == len(raw)
    assert m["class_id"] == 19 and m["class_name"] == "cow" and m["names"]["19"] == "cow"
    assert len(m["names"]) == 80
    assert m["input_shape"] == INPUT
    assert sorted(m["output_shapes"]) == sorted([OUT0, OUT1])
    assert m["ultralytics_version"] and m["date"]
    if PT.exists():
        assert m["source_pt_sha256"] == sha256_file(PT), "el .pt de origen no es el que declara el manifiesto"


def test_app_reads_cow_class_from_manifest():
    """config.ts toma COW_COCO_CLASS del manifiesto, no de un literal."""
    src = CONFIG_TS.read_text()
    assert "MANIFIESTO_SEGMENTADOR" in src
    assert not re.search(r"COW_COCO_CLASS(\s*:\s*number)?\s*=\s*\d+", src), "COW_COCO_CLASS vuelve a ser un literal"


@pytest.mark.slow
def test_apk_tflite_contract():
    pytest.importorskip("ai_edge_litert")
    if not APK_TFLITE.exists():
        pytest.skip("sin app/assets/model_bundle/yolo26n-seg.tflite")
    from ai_edge_litert.interpreter import Interpreter
    it = Interpreter(model_path=str(APK_TFLITE))
    assert it.get_input_details()[0]["shape"].tolist() == INPUT
    outs = sorted(d["shape"].tolist() for d in it.get_output_details())
    assert outs == sorted([OUT0, OUT1])


@pytest.mark.slow
def test_export_reproduces_apk_model_body(tmp_path):
    pytest.importorskip("litert_torch")
    pytest.importorskip("ai_edge_litert")
    if not PT.exists() or not APK_TFLITE.exists():
        pytest.skip("faltan models/yolo26n-seg.pt o el .tflite del APK")
    from ultralytics import YOLO
    src = tmp_path / "yolo26n-seg.pt"
    shutil.copy(PT, src)
    out = Path(YOLO(str(src)).export(format="litert", imgsz=640, device="cpu"))
    assert out.exists()
    from ai_edge_litert.interpreter import Interpreter
    it = Interpreter(model_path=str(out))
    assert it.get_input_details()[0]["shape"].tolist() == INPUT
    assert sorted(d["shape"].tolist() for d in it.get_output_details()) == sorted([OUT0, OUT1])
    exported = body(out.read_bytes())
    deployed = body(APK_TFLITE.read_bytes())
    assert hashlib.sha256(exported).hexdigest() == hashlib.sha256(deployed).hexdigest(), \
        "el cuerpo del modelo exportado difiere del que lleva el APK"
