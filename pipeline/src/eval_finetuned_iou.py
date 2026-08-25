"""Evaluación HONESTA del fine-tuning: IoU en el conjunto de VALIDACIÓN (animales
held-out, no vistos en entrenamiento), comparando el modelo PREENTRENADO vs el
FINE-TUNED contra la misma máscara de referencia (reconstruida del label).

Como ambos modelos se comparan contra la MISMA referencia held-out, la comparación
relativa (¿mejora el fine-tuning?) es robusta aunque el IoU absoluto dependa de la
anotación. Reporta IoU medio y % > 0.5 para cada modelo.

    python3 src/eval_finetuned_iou.py --finetuned runs/seg_finetune/jersey/weights/best.pt --device mps
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path
import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from core.segmenter import CowSegmenter


def gt_mask_from_label(label_path: Path, W: int, H: int):
    """Rasteriza el polígono del label YOLO-seg a máscara binaria."""
    line = label_path.read_text().strip().split()
    pts = np.array(line[1:], dtype=float).reshape(-1, 2)
    pts[:, 0] *= W; pts[:, 1] *= H
    m = np.zeros((H, W), np.uint8)
    cv2.fillPoly(m, [pts.astype(np.int32)], 1)
    return m


def iou(a, b):
    inter = np.logical_and(a, b).sum()
    union = np.logical_or(a, b).sum()
    return float(inter / union) if union else 0.0


def largest_mask(seg, im):
    cows = seg.segment(im)
    if not cows:
        return None
    dom = max(cows, key=lambda c: c.area_px)
    return dom.mask


def eval_model(seg, val_imgs, lbl_dir):
    ious = []
    for img in val_imgs:
        im = cv2.imread(str(img))
        if im is None:
            continue
        H, W = im.shape[:2]
        lbl = lbl_dir / f"{img.stem}.txt"
        if not lbl.exists():
            continue
        gt = gt_mask_from_label(lbl, W, H)
        pred = largest_mask(seg, im)
        ious.append(iou(pred, gt) if pred is not None else 0.0)
    arr = np.array(ious)
    return arr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--finetuned", required=True, help="ruta a best.pt del fine-tuning")
    ap.add_argument("--pretrained", default="models/yolo26n-seg.pt")
    ap.add_argument("--dataset", default="data/field/seg_dataset")
    ap.add_argument("--device", default="")
    a = ap.parse_args()

    ds = Path(a.dataset)
    val_imgs = sorted(p for p in (ds / "images" / "val").iterdir()
                      if p.suffix.lower() in (".jpg", ".jpeg", ".png"))
    lbl_dir = ds / "labels" / "val"
    print(f"val (held-out): {len(val_imgs)} imágenes\n")

    # preentrenado: clase COCO cow=19 ; fine-tuned: clase 0 (data.yaml names 0: cow)
    pre = CowSegmenter(a.pretrained, cow_class_id=19, min_confidence=0.45, device=a.device)
    fin = CowSegmenter(a.finetuned, cow_class_id=0, min_confidence=0.45, device=a.device)

    print(f"{'modelo':16} {'IoU medio':>10} {'%>0.5':>8} {'n':>5}")
    print("-" * 44)
    for name, seg in [("preentrenado", pre), ("fine-tuned", fin)]:
        arr = eval_model(seg, val_imgs, lbl_dir)
        pct = float((arr > 0.5).mean() * 100) if len(arr) else 0.0
        print(f"{name:16} {arr.mean():>10.3f} {pct:>7.1f}% {len(arr):>5}")
    print("\n(comparación RELATIVA sobre los mismos animales held-out: ¿el fine-tuning supera al preentrenado?)")


if __name__ == "__main__":
    raise SystemExit(main())
