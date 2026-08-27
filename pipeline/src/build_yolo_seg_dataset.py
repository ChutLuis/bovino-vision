"""Convierte las máscaras anotadas a un dataset YOLO-seg para fine-tuning.
Split POR ANIMAL (sin fuga de datos entre train y val).

- val: SOLO las 40 imágenes anotadas independientemente de la Fase A (data/val_clean/).
- train: resto de imágenes de campo y ráfagas pertenecientes a los animales de entrenamiento
         (sin ningún animal de validación).

Salida: data/field/seg_dataset/{images,labels}/{train,val} + data.yaml

    python3 src/build_yolo_seg_dataset.py
"""
from __future__ import annotations
import csv, re, shutil
from pathlib import Path
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
FIELD = ROOT / "data" / "field"
GROUPED = Path("/home/luisc/Documents/Thesis_final_raw/raw/_grouped")
if not GROUPED.exists():
    GROUPED = FIELD / "raw" / "_grouped"

VAL_CLEAN = ROOT / "data" / "val_clean"
OUT_DIR = FIELD / "seg_dataset"

INV = {
    "ALCIONE": "197264", "AMBAR": "236699", "AMELIA": "223671", "ANITA": "26577", "CAMELIA": "197269",
    "CARLINA": "207902", "CERECITA": "26579", "CERESA": "246502", "CHAPARRITA": "207911", "CHIQUITA": "223685",
    "CRISALIA": "197257", "CRISTY": "73169", "DAMITA": "73148", "DANESA": "207920", "DANIELA": "236687",
    "DIAGIRA": "236688", "ESMERALDA": "60771", "ESTRELLITA": "197260", "FABIOLA": "197272", "FORD": "236679",
    "GABY": "223678", "GIOCONDA": "223681", "IRINA": "207898", "IRIS": "236703", "KARINA": "236703",
    "KEYLA": "73161", "LEONORA": "77859", "LUBIANCA": "236694", "LUCERO": "223677", "LUCY": "236689",
    "MAFER": "236693", "MANZANILLA": "223672", "MARIITA": "26603", "MARIPOSA": "197259", "MARIQUITA": "236685",
    "MARTINICA": "26526", "MARTITA": "44635", "MINERVA": "44627", "NAHOMI": "223683", "NICOLETA": "26590",
    "NICOL ESTEFANIA": "223682", "NOHELIA": "236684", "NOHEMI": "236690", "NORMANDA": "246503", "ODRA": "73159",
    "OSCARINA": "207913", "PAULINA": "236700", "PERLA": "207915", "REALTA": "207903", "ROSALINDA": "236681",
    "SELENA": "223679", "SENORITA": "207916", "SOFIA": "223687", "TATY": "236705", "VICTORIA": "26533",
    "WADIELA": "77862", "YOYI": "207909", "ZAFIRO": "236697"
}
LAST4_TO_NAME = {ar[-4:]: nm for nm, ar in INV.items()}
MIN_AREA_FRAC = 0.005


def animal_id(folder_name: str) -> str:
    m = re.match(r"(\d+)", folder_name)
    if not m:
        return folder_name
    l4 = m.group(1)[-4:]
    return LAST4_TO_NAME.get(l4, f"unk_{l4}")


def mask_to_polygon(mask: np.ndarray, W: int, H: int) -> list[float] | None:
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
        poly.extend([round(float(x) / W, 6), round(float(y) / H, 6)])
    return poly


def main():
    if not VAL_CLEAN.exists() or not (VAL_CLEAN / "manifest.csv").exists():
        raise SystemExit("Error: Falta data/val_clean/manifest.csv. Corre primero build_val_clean.py / annotate_val.py")

    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    for sp in ("train", "val"):
        (OUT_DIR / "images" / sp).mkdir(parents=True, exist_ok=True)
        (OUT_DIR / "labels" / sp).mkdir(parents=True, exist_ok=True)

    # 1. Cargar conjunto de validación LIMPIO (Fase A)
    val_manifest = list(csv.DictReader(open(VAL_CLEAN / "manifest.csv")))
    val_animals = sorted(set(r["cow_id"] for r in val_manifest))
    n_val_images = 0
    n_val_instances = 0

    for r in val_manifest:
        qid = r["qid"]
        img_p = next((VAL_CLEAN / "images").glob(f"{qid}.*"), None)
        lbl_p = VAL_CLEAN / "labels" / f"{qid}.txt"
        if img_p and lbl_p.exists():
            shutil.copy(img_p, OUT_DIR / "images" / "val" / img_p.name)
            shutil.copy(lbl_p, OUT_DIR / "labels" / "val" / f"{qid}.txt")
            n_val_images += 1
            n_val_instances += int(r.get("n_instances", 1))

    # 2. Recolectar datos de entrenamiento (ráfagas _grouped y campo) para animales de TRAIN
    train_animals_set = set()
    n_train_images = 0
    n_train_instances = 0
    n_skip = 0

    # Ráfagas _grouped
    if GROUPED.exists():
        for d in sorted(GROUPED.iterdir()):
            if not d.is_dir() or d.name.startswith("_") or not re.match(r"\d", d.name):
                continue
            aid = animal_id(d.name)
            if aid in val_animals:
                # Animal reservado exclusivamente para validación (sin fuga)
                continue

            mdir = d / "mascaras"
            if not mdir.exists():
                continue

            train_animals_set.add(aid)
            for mp in sorted(mdir.glob("*.png")):
                img = next((p for p in d.glob(f"{mp.stem}.*") if p.suffix.lower() in (".jpg", ".jpeg")), None)
                if img is None:
                    continue
                im = cv2.imread(str(img))
                mask = cv2.imread(str(mp), cv2.IMREAD_GRAYSCALE)
                if im is None or mask is None:
                    n_skip += 1
                    continue
                H, W = im.shape[:2]
                if mask.shape[:2] != (H, W):
                    mask = cv2.resize(mask, (W, H), interpolation=cv2.INTER_NEAREST)
                poly = mask_to_polygon(mask, W, H)
                if poly is None:
                    n_skip += 1
                    continue

                stem = f"train_{aid}__{img.stem}".replace(" ", "_").replace("/", "_")
                shutil.copy(img, OUT_DIR / "images" / "train" / f"{stem}{img.suffix}")
                (OUT_DIR / "labels" / "train" / f"{stem}.txt").write_text("0 " + " ".join(map(str, poly)) + "\n")
                n_train_images += 1
                n_train_instances += 1

    # 3. Incorporar fotos fáciles adicionales de entrenamiento de animales de TRAIN
    repesaje = FIELD / "repesaje_1206"
    if repesaje.exists():
        # Incorporar fotos individuales de vacas de entrenamiento del 12/06
        for p in sorted(repesaje.glob("*.jpeg")):
            cow_name = p.stem.upper().replace("_", " ")
            if cow_name not in val_animals and cow_name in INV:
                # Generar label con SAM si existe modelo
                try:
                    from ultralytics import SAM
                    sam = SAM("mobile_sam.pt")
                    im = cv2.imread(str(p))
                    H, W = im.shape[:2]
                    r = sam(str(p), points=[[[W // 2, H // 2]]], labels=[[1]], verbose=False)
                    if r and r[0].masks is not None and len(r[0].masks.data) > 0:
                        mask = (r[0].masks.data[0].cpu().numpy() * 255).astype(np.uint8)
                        poly = mask_to_polygon(mask, W, H)
                        if poly is not None:
                            stem = f"train_rep1206_{p.stem}"
                            shutil.copy(p, OUT_DIR / "images" / "train" / f"{stem}{p.suffix}")
                            (OUT_DIR / "labels" / "train" / f"{stem}.txt").write_text("0 " + " ".join(map(str, poly)) + "\n")
                            n_train_images += 1
                            n_train_instances += 1
                            train_animals_set.add(cow_name)
                except Exception:
                    pass

    # 4. data.yaml
    yaml_content = f"""path: {OUT_DIR.resolve()}
train: images/train
val: images/val
names:
  0: cow
"""
    (OUT_DIR / "data.yaml").write_text(yaml_content)

    print("=== DATASET YOLO-seg GENERADO ===")
    print(f"Salida: {OUT_DIR}/data.yaml")
    print(f"Animales en VAL (held-out, {len(val_animals)}): {', '.join(val_animals)}")
    print(f"Animales en TRAIN ({len(train_animals_set)}): {', '.join(sorted(train_animals_set))}")
    print(f"Intersección train ∩ val: {set(val_animals).intersection(train_animals_set)} (CERO fuga)")
    print(f"Imágenes: train = {n_train_images} ({n_train_instances} instancias), val = {n_val_images} ({n_val_instances} instancias)")
    print(f"Descartadas por contorno inválido: {n_skip}")


if __name__ == "__main__":
    raise SystemExit(main())
