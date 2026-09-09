"""Fine-tuning de YOLO26-seg sobre el dataset generado por build_yolo_seg_dataset.py.
Aplica aumento de datos (HSV, flip horizontal, escala, rotación y mosaic de Ultralytics).

    python3 src/build_yolo_seg_dataset.py            # 1) generar dataset (verifica fuga)
    python3 src/finetune_segmenter.py                # 2) auto-detecta cuda:0 / mps / cpu
    python3 src/eval_finetuned_iou.py --models pre=models/yolo26n-seg.pt:19 nuevo=<ruta best.pt>:0 --visual

Dónde quedan los pesos:
  - Ultralytics 8.4 anida un `project` relativo bajo runs_dir/<task>/: con project="runs" y
    name="seg_finetune_jersey" el resultado real es runs/segment/runs/seg_finetune_jersey/weights/best.pt.
  - Este script copia best.pt a models/finetuned_<AAAAMMDD>_<sha8>.pt y NUNCA sobrescribe un archivo
    existente. models/yolo26n-seg-finetuned.pt (10 jun 2026, sha256 d6c65749…) se conserva intacto.

Notas de entrenamiento:
  - Con --optimizer auto (default de Ultralytics) se IGNORA --lr0: para datasets pequeños elige
    AdamW con lr0 = 0.002·5/(4+nc). Para controlar la tasa hay que fijar --optimizer AdamW --lr0 <x>.
  - El warmup dura al menos 100 iteraciones (≈4 épocas con 390 imágenes y batch 16): una corrida
    de 1 época no informa nada.
  - --freeze N congela las primeras N capas (10 = backbone) y reduce olvido y tiempo en CPU.
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
from datetime import date
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parent.parent


def detect_device() -> tuple[str, int]:
    """cuda:0 (80 épocas) si nvidia-smi y torch ven GPU; mps (80); si no, cpu (50)."""
    try:
        res = subprocess.run(["nvidia-smi"], capture_output=True, text=True)
        if res.returncode == 0 and torch.cuda.is_available():
            return "cuda:0", 80
    except Exception:
        pass
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps", 80
    return "cpu", 50


def main():
    default_dev, default_epochs = detect_device()

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", default=str(ROOT / "data/field/seg_dataset/data.yaml"))
    ap.add_argument("--model", default=str(ROOT / "models/yolo26n-seg.pt"))
    ap.add_argument("--epochs", type=int, default=default_epochs)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--device", default=default_dev, help='"", "cuda:0", "mps", "cpu"')
    ap.add_argument("--patience", type=int, default=20, help="early stopping")
    ap.add_argument("--freeze", type=int, default=None, help="capas a congelar (10 = backbone)")
    ap.add_argument("--optimizer", default="auto", help="auto | AdamW | SGD ... (auto ignora --lr0)")
    ap.add_argument("--lr0", type=float, default=None, help="solo tiene efecto si --optimizer != auto")
    ap.add_argument("--name", default="seg_finetune_jersey")
    a = ap.parse_args()

    data_path = Path(a.data)
    if not data_path.exists():
        raise SystemExit(f"falta {a.data} — corre primero build_yolo_seg_dataset.py")

    print(f"Dispositivo: {a.device} | Épocas: {a.epochs} | Batch: {a.batch} | freeze: {a.freeze} | optimizer: {a.optimizer}")
    if a.device == "cpu":
        torch.set_num_threads(12)

    extra = {}
    if a.freeze is not None:
        extra["freeze"] = a.freeze
    if a.optimizer != "auto":
        extra["optimizer"] = a.optimizer
        if a.lr0 is not None:
            extra["lr0"] = a.lr0
    elif a.lr0 is not None:
        print("aviso: --lr0 se ignora con --optimizer auto")

    from ultralytics import YOLO
    model = YOLO(a.model)
    results = model.train(
        data=str(data_path.resolve()),
        epochs=a.epochs,
        imgsz=a.imgsz,
        batch=a.batch,
        device=a.device,
        patience=a.patience,
        cache=True,
        project="runs",
        name=a.name,
        exist_ok=True,
        # aumento explícito (hace real el "aumento de datos" del Cap. 3); valores conservadores
        hsv_h=0.015,
        hsv_s=0.5,
        hsv_v=0.4,
        fliplr=0.5,
        scale=0.4,
        degrees=10.0,
        seed=0,
        verbose=True,
        **extra,
    )

    save_dir = Path(results.save_dir) if hasattr(results, "save_dir") else None
    best = save_dir / "weights" / "best.pt" if save_dir else None
    if best is None or not best.exists():
        print(f"\nAviso: no se encontró best.pt en {save_dir}")
        return 1

    sha8 = hashlib.sha256(best.read_bytes()).hexdigest()[:8]
    dest = ROOT / "models" / f"finetuned_{date.today().strftime('%Y%m%d')}_{sha8}.pt"
    if dest.exists():
        print(f"\n{dest} ya existe (mismo contenido); no se sobrescribe.")
    else:
        shutil.copy(best, dest)
    print(f"\n✓ best.pt: {best}\n✓ copia con hash: {dest}")
    print(f"\nEvalúa contra las máscaras manuales:\n  python3 src/eval_finetuned_iou.py --models "
          f"pre=models/yolo26n-seg.pt:19 nuevo={dest.relative_to(ROOT)}:0 --visual")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
