"""Convierte las máscaras anotadas (_grouped/*/mascaras/*.png) a un dataset YOLO-seg
para fine-tuning del segmentador. Split POR ANIMAL (sin fuga de datos).

Para CADA máscara:
  - localiza su foto, extrae el contorno mayor -> polígono normalizado (formato YOLO-seg)
  - escribe label .txt: "0 x1 y1 x2 y2 ... xn yn"  (clase 0 = cow)
Agrupa carpetas del MISMO animal (6590/6590_2/... = Nicoleta) y reparte animales 80/20
entre train/val, de modo que ningún animal aparezca en ambos (IoU de val = honesto).
Usa TODAS las vacas (pesadas o no) — la segmentación no depende del peso.

Salida: data/field/seg_dataset/{images,labels}/{train,val} + data.yaml

    python3 src/build_yolo_seg_dataset.py
"""
from __future__ import annotations
import re, shutil, unicodedata
from pathlib import Path
import cv2
import numpy as np

INV = {
 "ALCIONE":"197264","AMBAR":"236699","AMELIA":"223671","ANITA":"26577","CAMELIA":"197269",
 "CARLINA":"207902","CERECITA":"26579","CERESA":"246502","CHAPARRITA":"207911","CHIQUITA":"223685",
 "CRISALIA":"197257","CRISTY":"73169","DAMITA":"73148","DANESA":"207920","DANIELA":"236687",
 "DIAGIRA":"236688","ESMERALDA":"60771","ESTRELLITA":"197260","FABIOLA":"197272","FORD":"236679",
 "GABY":"223678","GIOCONDA":"223681","IRINA":"207898","IRIS":"236703","KARINA":"236703",
 "KEYLA":"73161","LEONORA":"77859","LUBIANCA":"236694","LUCERO":"223677","LUCY":"236689",
 "MAFER":"236693","MANZANILLA":"223672","MARIITA":"26603","MARIPOSA":"197259","MARIQUITA":"236685",
 "MARTINICA":"26526","MARTITA":"44635","MINERVA":"44627","NAHOMI":"223683","NICOLETA":"26590",
 "NICOL ESTEFANIA":"223682","NOHELIA":"236684","NOHEMI":"236690","NORMANDA":"246503","ODRA":"73159",
 "OSCARINA":"207913","PAULINA":"236700","PERLA":"207915","REALTA":"207903","ROSALINDA":"236681",
 "SELENA":"223679","SENORITA":"207916","SOFIA":"223687","TATY":"236705","VICTORIA":"26533",
 "WADIELA":"77862","YOYI":"207909","ZAFIRO":"236697"}
last4_to_name = {ar[-4:]: nm for nm, ar in INV.items()}

field = Path("data/field")
grouped = field / "raw" / "_grouped"
out = field / "seg_dataset"
MIN_AREA_FRAC = 0.01   # descarta máscaras minúsculas
VAL_EVERY = 5          # ~20% de animales a val


def animal_id(folder_name: str) -> str:
    m = re.match(r"(\d+)", folder_name)
    if not m:
        return folder_name
    l4 = m.group(1)[-4:]
    return last4_to_name.get(l4, f"unk_{l4}")


def mask_to_polygon(mask: np.ndarray, W: int, H: int):
    """Contorno mayor -> lista de puntos normalizados [x1,y1,...]. None si degenerado."""
    cnts, _ = cv2.findContours((mask > 127).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None
    c = max(cnts, key=cv2.contourArea)
    if cv2.contourArea(c) < MIN_AREA_FRAC * W * H:
        return None
    eps = 0.0015 * cv2.arcLength(c, True)
    c = cv2.approxPolyDP(c, eps, True).reshape(-1, 2)
    if len(c) < 3:
        return None
    poly = []
    for x, y in c:
        poly += [round(float(x) / W, 6), round(float(y) / H, 6)]
    return poly


def main():
    if out.exists():
        shutil.rmtree(out)
    for sp in ("train", "val"):
        (out / "images" / sp).mkdir(parents=True, exist_ok=True)
        (out / "labels" / sp).mkdir(parents=True, exist_ok=True)

    # recolecta (animal -> [(img_path, mask_path)])
    by_animal: dict[str, list] = {}
    for d in sorted(grouped.iterdir()):
        if not d.is_dir() or d.name.startswith("_") or not re.match(r"\d", d.name):
            continue
        mdir = d / "mascaras"
        if not mdir.exists():
            continue
        aid = animal_id(d.name)
        for mp in sorted(mdir.glob("*.png")):
            img = next((p for p in d.glob(f"{mp.stem}.*") if p.suffix.lower() in (".jpg", ".jpeg")), None)
            if img:
                by_animal.setdefault(aid, []).append((img, mp))

    animals = sorted(by_animal)
    n_img = {"train": 0, "val": 0}
    n_skip = 0
    train_animals, val_animals = [], []
    for i, aid in enumerate(animals):
        split = "val" if (i % VAL_EVERY == 0) else "train"
        (val_animals if split == "val" else train_animals).append(aid)
        for img, mp in by_animal[aid]:
            im = cv2.imread(str(img)); mask = cv2.imread(str(mp), cv2.IMREAD_GRAYSCALE)
            if im is None or mask is None:
                n_skip += 1; continue
            H, W = im.shape[:2]
            if mask.shape[:2] != (H, W):
                mask = cv2.resize(mask, (W, H), interpolation=cv2.INTER_NEAREST)
            poly = mask_to_polygon(mask, W, H)
            if poly is None:
                n_skip += 1; continue
            stem = f"{aid}__{img.stem}".replace(" ", "_").replace("/", "_")
            shutil.copy(img, out / "images" / split / f"{stem}{img.suffix}")
            (out / "labels" / split / f"{stem}.txt").write_text("0 " + " ".join(map(str, poly)) + "\n")
            n_img[split] += 1

    (out / "data.yaml").write_text(
        f"path: {out.resolve()}\ntrain: images/train\nval: images/val\nnames:\n  0: cow\n")

    print(f"animales: {len(animals)} (train {len(train_animals)}, val {len(val_animals)})")
    print(f"imágenes: train {n_img['train']}, val {n_img['val']}  | descartadas {n_skip}")
    print(f"val animals (held-out): {', '.join(val_animals)}")
    print(f"-> {out}/data.yaml")


if __name__ == "__main__":
    raise SystemExit(main())
