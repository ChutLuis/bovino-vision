"""Convierte las máscaras anotadas a un dataset YOLO-seg para fine-tuning.
Split POR ANIMAL, sin fuga entre train y val, verificado por nombre, por arete y por hash.

- val  : SOLO las imágenes del manifiesto de data/val_clean/ (anotadas a mano con annotate_val.py).
- train: máscaras de ráfagas (_grouped/<arete4>/mascaras/*.png) de animales que NO están en val.
         Un animal está en val si su nombre aparece en el manifiesto O si comparte arete con
         uno que aparece (ALIASES: el inventario asigna 236703 a IRIS y a KARINA).
         Las carpetas sin identidad (unk_*) se excluyen salvo --include-unknown.
- Opcional (--sam-pseudolabels): fotos individuales de repesaje_1206 etiquetadas con MobileSAM
  (un punto al centro, sin revisión). Apagado por defecto: son etiquetas no verificadas.

Ruta de los crudos, en orden: --raw, $BOVINO_RAW_GROUPED, data/field/raw/_grouped,
~/Documents/Thesis_final_raw/raw/_grouped.

Salida: data/field/seg_dataset/{images,labels}/{train,val} + data.yaml (rutas relativas al yaml).
Al final se comprueba que train ∩ val = ∅ por sha256 y que ningún animal de train comparte
nombre o arete con uno de val; si falla, el script termina con error.

    python3 src/build_yolo_seg_dataset.py --dry-run     # solo cuenta y verifica, no escribe
    python3 src/build_yolo_seg_dataset.py               # regenera data/field/seg_dataset
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import os
import re
import shutil
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
FIELD = ROOT / "data" / "field"
VAL_CLEAN = ROOT / "data" / "val_clean"
OUT_DIR = FIELD / "seg_dataset"
REPESAJE = FIELD / "repesaje_1206"
RAW_CANDIDATES = (
    os.environ.get("BOVINO_RAW_GROUPED"),
    FIELD / "raw" / "_grouped",
    Path.home() / "Documents" / "Thesis_final_raw" / "raw" / "_grouped",
)

# Inventario LACAMAMI (WhatsApp Image 2026-06-09 at 13.37.37.jpeg): nombre -> arete de trazabilidad.
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
    "WADIELA": "77862", "YOYI": "207909", "ZAFIRO": "236697",
}
# Aretes que el inventario asigna a más de un animal. Para el split se tratan como UN grupo:
# si uno está en val, ninguno del grupo entra a train.
ALIASES = {"236703": ("IRIS", "KARINA")}
LAST4_TO_NAME = {ar[-4:]: nm for nm, ar in INV.items()}
MIN_AREA_FRAC = 0.005


def arete_group(name: str) -> frozenset[str]:
    """Nombres indistinguibles por arete de `name` (incluye a `name`)."""
    ar = INV.get(name)
    if ar is None:
        return frozenset({name})
    return frozenset(ALIASES.get(ar, (name,))) | {name}


def expand_val_animals(names) -> set[str]:
    out: set[str] = set()
    for n in names:
        out |= arete_group(n)
    return out


def duplicated_aretes_without_alias() -> dict[str, list[str]]:
    by_arete: dict[str, list[str]] = {}
    for nm, ar in INV.items():
        by_arete.setdefault(ar, []).append(nm)
    return {ar: nms for ar, nms in by_arete.items() if len(nms) > 1 and ar not in ALIASES}


def animal_id(folder_name: str) -> str:
    m = re.match(r"(\d+)", folder_name)
    if not m:
        return folder_name
    l4 = m.group(1)[-4:]
    return LAST4_TO_NAME.get(l4, f"unk_{l4}")


def train_stem_to_animal(stem: str) -> str:
    """Inverso del nombre de archivo de train: train_<AID>__<foto> o train_rep1206_<nombre>."""
    if stem.startswith("train_rep1206_"):
        return stem[len("train_rep1206_"):].upper().replace("_", " ")
    if stem.startswith("train_"):
        return stem[len("train_"):].split("__", 1)[0].replace("_", " ")
    return stem


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


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def resolve_grouped(cli_raw: str | None, strict: bool = True) -> Path:
    """Directorio _grouped de las ráfagas: --raw, $BOVINO_RAW_GROUPED, data/field/raw/_grouped, ~/Documents/...

    Con strict=False devuelve el último candidato aunque no exista (para módulos que fijan rutas al
    importarse, como annotate_val.py y build_val_clean.py); el error aparece al abrir la imagen."""
    for cand in (cli_raw, *RAW_CANDIDATES):
        if cand and Path(cand).expanduser().is_dir():
            return Path(cand).expanduser()
    if not strict:
        return Path(RAW_CANDIDATES[-1])
    raise SystemExit("No encuentro las ráfagas _grouped. Usa --raw <dir> o exporta BOVINO_RAW_GROUPED "
                     "(copia íntegra en Thesis_final_raw/raw/_grouped, verificable con MANIFEST.sha1).")


def plan_val(val_manifest: list[dict]) -> list[dict]:
    items = []
    for r in val_manifest:
        qid = r["qid"]
        img_p = next((VAL_CLEAN / "images").glob(f"{qid}.*"), None)
        lbl_p = VAL_CLEAN / "labels" / f"{qid}.txt"
        if img_p is None or not lbl_p.exists():
            print(f"  aviso: {qid} sin imagen o sin label en val_clean, se omite")
            continue
        items.append({"qid": qid, "img": img_p, "lbl": lbl_p, "animal": r["cow_id"],
                      "n_inst": int(r.get("n_polygons") or r.get("n_instances") or 1)})
    return items


def plan_train_grouped(grouped: Path, val_animals: set[str], include_unknown: bool) -> tuple[list[dict], dict]:
    items, stats = [], {"skip_val_animal": 0, "skip_unknown": 0, "skip_contour": 0, "skip_noimg": 0}
    for d in sorted(grouped.iterdir()):
        if not d.is_dir() or d.name.startswith("_") or not re.match(r"\d", d.name):
            continue
        aid = animal_id(d.name)
        if aid in val_animals:
            stats["skip_val_animal"] += 1
            continue
        if aid.startswith("unk_") and not include_unknown:
            stats["skip_unknown"] += 1
            continue
        mdir = d / "mascaras"
        if not mdir.exists():
            continue
        for mp in sorted(mdir.glob("*.png")):
            img = next((p for p in d.glob(f"{mp.stem}.*") if p.suffix.lower() in (".jpg", ".jpeg")), None)
            if img is None:
                stats["skip_noimg"] += 1
                continue
            im = cv2.imread(str(img))
            mask = cv2.imread(str(mp), cv2.IMREAD_GRAYSCALE)
            if im is None or mask is None:
                stats["skip_contour"] += 1
                continue
            H, W = im.shape[:2]
            if mask.shape[:2] != (H, W):
                mask = cv2.resize(mask, (W, H), interpolation=cv2.INTER_NEAREST)
            poly = mask_to_polygon(mask, W, H)
            if poly is None:
                stats["skip_contour"] += 1
                continue
            stem = f"train_{aid}__{img.stem}".replace(" ", "_").replace("/", "_")
            items.append({"img": img, "stem": stem, "poly": poly, "animal": aid, "src": d.name})
    return items, stats


def plan_train_sam(val_animals: set[str], dry_run: bool) -> list[dict]:
    """Pseudo-etiquetas MobileSAM para fotos individuales del repesaje 12/06 (solo con --sam-pseudolabels)."""
    if not REPESAJE.exists():
        return []
    cands = [p for p in sorted(REPESAJE.glob("*.jpeg"))
             if p.stem.upper().replace("_", " ") in INV and p.stem.upper().replace("_", " ") not in val_animals]
    if dry_run:
        return [{"img": p, "stem": f"train_rep1206_{p.stem}", "poly": None, "animal": p.stem.upper().replace("_", " "),
                 "src": "repesaje_1206 (SAM, sin calcular en dry-run)"} for p in cands]
    from ultralytics import SAM
    sam = SAM(str(ROOT / "mobile_sam.pt"))
    items = []
    for p in cands:
        im = cv2.imread(str(p))
        if im is None:
            continue
        H, W = im.shape[:2]
        r = sam(str(p), points=[[[W // 2, H // 2]]], labels=[[1]], verbose=False)
        if not r or r[0].masks is None or len(r[0].masks.data) == 0:
            print(f"  aviso: SAM no segmentó {p.name}")
            continue
        mask = (r[0].masks.data[0].cpu().numpy() * 255).astype(np.uint8)
        if mask.shape[:2] != (H, W):
            mask = cv2.resize(mask, (W, H), interpolation=cv2.INTER_NEAREST)
        poly = mask_to_polygon(mask, W, H)
        if poly is None:
            continue
        items.append({"img": p, "stem": f"train_rep1206_{p.stem}", "poly": poly,
                      "animal": p.stem.upper().replace("_", " "), "src": "repesaje_1206 (SAM)"})
    return items


def check_no_leak(train_items: list[dict], val_items: list[dict]) -> list[str]:
    """Devuelve la lista de violaciones (vacía = sin fuga). Compara nombre, grupo de arete y sha256."""
    problems = []
    val_animals = expand_val_animals(v["animal"] for v in val_items)
    for t in train_items:
        if t["animal"] in val_animals:
            problems.append(f"{t['stem']}: animal {t['animal']} está en val (por nombre o arete)")
    val_hashes = {sha256_file(v["img"]) for v in val_items}
    val_clean_hashes = {sha256_file(p) for p in (VAL_CLEAN / "images").iterdir() if p.is_file()}
    for t in train_items:
        h = sha256_file(t["img"])
        if h in val_hashes:
            problems.append(f"{t['stem']}: misma imagen (sha256) que una de val")
        elif h in val_clean_hashes:
            problems.append(f"{t['stem']}: misma imagen (sha256) que una de data/val_clean/images")
    return problems


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw", help="directorio _grouped con las ráfagas")
    ap.add_argument("--out", default=str(OUT_DIR))
    ap.add_argument("--dry-run", action="store_true", help="no escribe nada: cuenta, lista y verifica fuga")
    ap.add_argument("--include-unknown", action="store_true", help="incluir carpetas unk_* en train")
    ap.add_argument("--sam-pseudolabels", action="store_true", help="añadir repesaje_1206 etiquetado con MobileSAM")
    a = ap.parse_args(argv)

    out_dir = Path(a.out)
    dup = duplicated_aretes_without_alias()
    if dup:
        raise SystemExit(f"INV tiene aretes repetidos sin declarar en ALIASES: {dup}")
    if not (VAL_CLEAN / "manifest.csv").exists():
        raise SystemExit("Falta data/val_clean/manifest.csv. Corre primero annotate_val.py")

    grouped = resolve_grouped(a.raw)
    val_manifest = list(csv.DictReader(open(VAL_CLEAN / "manifest.csv")))
    val_items = plan_val(val_manifest)
    val_names = sorted({v["animal"] for v in val_items})
    val_animals = expand_val_animals(val_names)
    train_items, stats = plan_train_grouped(grouped, val_animals, a.include_unknown)
    sam_items = plan_train_sam(val_animals, a.dry_run) if a.sam_pseudolabels else []
    train_items += sam_items

    problems = check_no_leak(train_items, val_items)
    train_animals = sorted({t["animal"] for t in train_items})

    print("=== DATASET YOLO-seg" + (" (DRY-RUN, no se escribe nada)" if a.dry_run else "") + " ===")
    print(f"Crudos: {grouped}")
    print(f"Salida: {out_dir}")
    print(f"Animales en VAL ({len(val_names)}): {', '.join(val_names)}")
    extra = sorted(val_animals - set(val_names))
    if extra:
        print(f"  + excluidos de train por compartir arete: {', '.join(extra)}")
    print(f"Animales en TRAIN ({len(train_animals)}): {', '.join(train_animals)}")
    print(f"Imágenes: train = {len(train_items)} ({len(sam_items)} pseudo-etiquetas SAM), "
          f"val = {len(val_items)} ({sum(v['n_inst'] for v in val_items)} instancias)")
    print(f"Carpetas saltadas: {stats['skip_val_animal']} de animales val, {stats['skip_unknown']} sin identidad (unk_*); "
          f"máscaras descartadas por contorno: {stats['skip_contour']}; sin imagen: {stats['skip_noimg']}")
    if problems:
        print("\nFUGA DETECTADA:")
        for p in problems:
            print("  -", p)
        return 2
    print("Fuga train∩val por nombre, arete y sha256: NINGUNA")

    if a.dry_run:
        return 0

    if out_dir.exists():
        shutil.rmtree(out_dir)
    for sp in ("train", "val"):
        (out_dir / "images" / sp).mkdir(parents=True, exist_ok=True)
        (out_dir / "labels" / sp).mkdir(parents=True, exist_ok=True)
    for v in val_items:
        shutil.copy(v["img"], out_dir / "images" / "val" / v["img"].name)
        shutil.copy(v["lbl"], out_dir / "labels" / "val" / f"{v['qid']}.txt")
    for t in train_items:
        shutil.copy(t["img"], out_dir / "images" / "train" / f"{t['stem']}{t['img'].suffix}")
        (out_dir / "labels" / "train" / f"{t['stem']}.txt").write_text("0 " + " ".join(map(str, t["poly"])) + "\n")
    # Sin `path:` Ultralytics resuelve train/val respecto al directorio del yaml (portátil entre máquinas).
    (out_dir / "data.yaml").write_text("train: images/train\nval: images/val\nnames:\n  0: cow\n")
    with open(out_dir / "split_report.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["split", "file", "animal", "source", "sha256"])
        for v in val_items:
            w.writerow(["val", v["img"].name, v["animal"], "val_clean", sha256_file(v["img"])])
        for t in train_items:
            w.writerow(["train", f"{t['stem']}{t['img'].suffix}", t["animal"], t["src"], sha256_file(t["img"])])
    print(f"Escrito {out_dir}/data.yaml y split_report.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
