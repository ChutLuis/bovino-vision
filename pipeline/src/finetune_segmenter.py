"""Fine-tuning de YOLO26-seg sobre las máscaras propias (dataset generado por
build_yolo_seg_dataset.py). Aplica data augmentation (default de Ultralytics:
HSV, flip, escala, mosaic) — con esto el "aumento de datos" del Cap 3 es REAL.

    python3 src/build_yolo_seg_dataset.py            # 1) generar dataset
    python3 src/finetune_segmenter.py --device mps   # 2) Mac (o cuda:0 en Jetson, cpu si no hay GPU)

Pesos resultantes: runs/seg_finetune/jersey/weights/best.pt
Luego evaluar honesto:
    python3 src/eval_finetuned_iou.py --finetuned runs/seg_finetune/jersey/weights/best.pt
"""
from __future__ import annotations
import argparse
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/field/seg_dataset/data.yaml")
    ap.add_argument("--model", default="models/yolo26n-seg.pt")
    ap.add_argument("--epochs", type=int, default=80)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--device", default="", help='"", "mps", "cuda:0", "cpu"')
    ap.add_argument("--patience", type=int, default=20, help="early stopping")
    a = ap.parse_args()

    if not Path(a.data).exists():
        raise SystemExit(f"falta {a.data} — corre primero build_yolo_seg_dataset.py")

    from ultralytics import YOLO
    model = YOLO(a.model)
    model.train(
        data=a.data, epochs=a.epochs, imgsz=a.imgsz, batch=a.batch,
        device=a.device or None, patience=a.patience,
        project="runs/seg_finetune", name="jersey", exist_ok=True,
        # augmentation explícita (vuelve real lo del Cap 3); valores conservadores
        hsv_h=0.015, hsv_s=0.5, hsv_v=0.4, fliplr=0.5, scale=0.4, degrees=10.0,
        seed=0, verbose=True,
    )
    print("\nPesos -> runs/seg_finetune/jersey/weights/best.pt")
    print("Evalúa: python3 src/eval_finetuned_iou.py --finetuned runs/seg_finetune/jersey/weights/best.pt")


if __name__ == "__main__":
    raise SystemExit(main())
