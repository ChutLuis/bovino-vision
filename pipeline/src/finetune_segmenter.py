"""Fine-tuning de YOLO26-seg sobre las máscaras propias (dataset generado por
build_yolo_seg_dataset.py). Aplica data augmentation (default de Ultralytics:
HSV, flip, escala, mosaic) — con esto el "aumento de datos" del Cap 3 es REAL.

    python3 src/build_yolo_seg_dataset.py            # 1) generar dataset
    python3 src/finetune_segmenter.py                # 2) auto-detecta cuda:0 o cpu (50 épocas en cpu)

Pesos resultantes:
  - runs/seg_finetune/jersey/weights/best.pt
  - models/yolo26n-seg-finetuned.pt
"""
from __future__ import annotations
import argparse, shutil, subprocess
from pathlib import Path
import torch


def detect_device() -> tuple[str, int]:
    """Detecta si hay GPU disponible con nvidia-smi -> cuda:0 (80 épocas), si no cpu (50 épocas)."""
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

    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/field/seg_dataset/data.yaml")
    ap.add_argument("--model", default="models/yolo26n-seg.pt")
    ap.add_argument("--epochs", type=int, default=default_epochs)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--device", default=default_dev, help='"", "cuda:0", "mps", "cpu"')
    ap.add_argument("--patience", type=int, default=20, help="early stopping")
    a = ap.parse_args()

    data_path = Path(a.data)
    if not data_path.exists():
        raise SystemExit(f"falta {a.data} — corre primero build_yolo_seg_dataset.py")

    print(f"Dispositivo detectado: {a.device} | Épocas configuradas: {a.epochs} | Batch: {a.batch}")
    if a.device == "cpu":
        torch.set_num_threads(12)

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
        name="seg_finetune_jersey",
        exist_ok=True,
        # augmentation explícita (vuelve real lo del Cap 3); valores conservadores
        hsv_h=0.015,
        hsv_s=0.5,
        hsv_v=0.4,
        fliplr=0.5,
        scale=0.4,
        degrees=10.0,
        seed=0,
        verbose=True,
    )

    # Ubicación canónica de pesos
    save_dir = Path(results.save_dir) if hasattr(results, "save_dir") else Path("runs/seg_finetune_jersey")
    best_weights = save_dir / "weights" / "best.pt"

    # Asegurar copia en runs/seg_finetune/jersey/weights/best.pt y models/yolo26n-seg-finetuned.pt
    canonical_run = Path("runs/seg_finetune/jersey/weights")
    canonical_run.mkdir(parents=True, exist_ok=True)
    if best_weights.exists():
        shutil.copy(best_weights, canonical_run / "best.pt")
        shutil.copy(best_weights, Path("models/yolo26n-seg-finetuned.pt"))
        print(f"\n✓ Pesos guardados en:")
        print(f"  - {canonical_run / 'best.pt'}")
        print(f"  - models/yolo26n-seg-finetuned.pt")
    else:
        print(f"\nAviso: no se encontró {best_weights}")

    print("\nEvalúa: python3 src/eval_finetuned_iou.py --finetuned models/yolo26n-seg-finetuned.pt")


if __name__ == "__main__":
    raise SystemExit(main())
