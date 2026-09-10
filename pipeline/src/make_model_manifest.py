"""Genera app/assets/model_bundle/model_manifest.json: la ficha del segmentador que lleva el APK.

Toma el .tflite desplegado (sha256 del archivo y del cuerpo sin el zip de metadatos que Ultralytics
anexa), sus metadatos de exportación (versión, fecha, nombres de clase) y el .pt de origen (sha256,
versión del checkpoint). El APK lee class_id desde aquí (app/src/vision/config.ts) y registra el
sha256 del segmentador en cada estimación (estimarPeso.ts); tests/test_export_contract.py comprueba
que el manifiesto coincide con el archivo. Volver a correr este script cada vez que cambie el .tflite.

    python3 src/make_model_manifest.py
    python3 src/make_model_manifest.py --pt /otra/ruta/yolo26n-seg.pt
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import zipfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUNDLE = ROOT.parent / "app" / "assets" / "model_bundle"
COW_CLASS_ID = 19


def body(b: bytes) -> bytes:
    i = b.find(b"PK\x03\x04")
    return b if i < 0 else b[:i]


def tflite_metadata(b: bytes) -> dict:
    i = b.find(b"PK\x03\x04")
    if i < 0:
        return {}
    with zipfile.ZipFile(io.BytesIO(b[i:])) as z:
        return json.loads(z.read("metadata.json")) if "metadata.json" in z.namelist() else {}


def tensor_shapes(path: Path) -> tuple[list[int] | None, list[list[int]] | None]:
    try:
        from ai_edge_litert.interpreter import Interpreter
    except ImportError:
        return None, None
    it = Interpreter(model_path=str(path))
    return (it.get_input_details()[0]["shape"].tolist(),
            sorted(d["shape"].tolist() for d in it.get_output_details()))


def pt_info(path: Path | None) -> dict:
    if path is None or not path.exists():
        return {"source_pt": None, "source_pt_sha256": None, "source_pt_ultralytics_version": None, "source_pt_date": None}
    import torch
    ck = torch.load(path, map_location="cpu", weights_only=False)
    return {"source_pt": path.name, "source_pt_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "source_pt_ultralytics_version": ck.get("version"), "source_pt_date": ck.get("date"),
            "source_pt_names_ok": ck["model"].names[COW_CLASS_ID] == "cow"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tflite", default=str(BUNDLE / "yolo26n-seg.tflite"))
    ap.add_argument("--pt", default=str(ROOT / "models" / "yolo26n-seg.pt"))
    ap.add_argument("--out", default=str(BUNDLE / "model_manifest.json"))
    a = ap.parse_args()

    tfl = Path(a.tflite)
    raw = tfl.read_bytes()
    meta = tflite_metadata(raw)
    names = {str(k): v for k, v in (meta.get("names") or {}).items()}
    if names and names.get(str(COW_CLASS_ID)) != "cow":
        raise SystemExit(f"los metadatos del .tflite no asignan 'cow' a la clase {COW_CLASS_ID}: {names.get(str(COW_CLASS_ID))}")
    inp, outs = tensor_shapes(tfl)
    imgsz = meta.get("imgsz", [640, 640])

    manifest = {
        "model_file": tfl.name,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "body_sha256": hashlib.sha256(body(raw)).hexdigest(),
        "size_bytes": len(raw),
        "format": "litert",
        "precision": "fp32" if not (meta.get("args") or {}).get("quantize") else str(meta["args"]["quantize"]),
        "task": meta.get("task", "segment"),
        "imgsz": imgsz[0] if isinstance(imgsz, list) else imgsz,
        "end2end": meta.get("end2end"),
        "input_shape": inp,
        "output_shapes": outs,
        "class_id": COW_CLASS_ID,
        "class_name": "cow",
        "names": names,
        "ultralytics_version": meta.get("version"),
        "date": meta.get("date"),
        **pt_info(Path(a.pt) if a.pt else None),
        "training": "Preentrenado COCO (Ultralytics). Sin ajuste fino: el fine-tuning evaluado el 9 sep 2026 fue peor (pipeline/FINETUNING.md).",
        "generated_by": "pipeline/src/make_model_manifest.py",
        "generated_at": date.today().isoformat(),
    }
    out = Path(a.out)
    out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({k: v for k, v in manifest.items() if k != "names"}, indent=1, ensure_ascii=False))
    print(f"-> {out}  (names: {len(names)} clases)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
