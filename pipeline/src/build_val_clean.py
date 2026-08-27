"""Generador del dataset de validación LIMPIO e INDEPENDIENTE (40 imágenes estratificadas).

Usa MobileSAM con prompts precisos por instancia (separando vacas en fotos multi-vaca).
Ninguna máscara de este conjunto proviene de YOLO (cumple el caveat de FINETUNING.md).

Salida:
  data/val_clean/images/{qid}.jpg
  data/val_clean/labels/{qid}.txt (YOLO-seg format)
  data/val_clean/masks/{qid}_inst{k}.png
  data/val_clean/overlays/{qid}.jpg
  data/val_clean/manifest.csv
"""
from __future__ import annotations
import csv, shutil
from pathlib import Path
import cv2
import numpy as np
from ultralytics import SAM

ROOT = Path(__file__).resolve().parent.parent
FIELD = ROOT / "data" / "field"
GROUPED = Path("/home/luisc/Documents/Thesis_final_raw/raw/_grouped")
REPESAJE = FIELD / "repesaje_1206"
OUT_DIR = ROOT / "data" / "val_clean"

COLORS = [
    (0, 230, 255),   # Amarillo/dorado
    (0, 255, 100),   # Verde
    (255, 100, 0),   # Azul
    (200, 0, 255),   # Magenta
    (0, 165, 255),   # Naranja
    (255, 255, 0),   # Cyan
]

MIN_AREA_FRAC = 0.005


def mask_to_polygon(mask: np.ndarray, W: int, H: int) -> list[float] | None:
    cnts, _ = cv2.findContours((mask > 0).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
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


# Definición exacta de las 40 imágenes estratificadas con sus prompts por instancia
QUEUE_SPEC = [
    # ==================== 15 FÁCILES (Laterales controladas 5/06) ====================
    {
        "stratum": "facil", "qid": "facil_01_perla", "cow": "PERLA",
        "path": FIELD / "WhatsApp Image 2026-06-05 at 07.57.46.jpeg",
        "instances": [{"pts": [[550, 500]], "lbs": [1]}],
    },
    {
        "stratum": "facil", "qid": "facil_02_odra", "cow": "ODRA",
        "path": FIELD / "WhatsApp Image 2026-06-05 at 07.58.08.jpeg",
        "instances": [{"pts": [[600, 480]], "lbs": [1]}],
    },
    {
        "stratum": "facil", "qid": "facil_03_mariquita", "cow": "MARIQUITA",
        "path": FIELD / "WhatsApp Image 2026-06-05 at 07.58.33.jpeg",
        "instances": [{"pts": [[600, 480]], "lbs": [1]}],
    },
    {
        "stratum": "facil", "qid": "facil_04_martita", "cow": "MARTITA",
        "path": FIELD / "WhatsApp Image 2026-06-05 at 07.58.52.jpeg",
        "instances": [{"pts": [[600, 500]], "lbs": [1]}],
    },
    {
        "stratum": "facil", "qid": "facil_05_lubianca", "cow": "LUBIANCA",
        "path": FIELD / "WhatsApp Image 2026-06-05 at 07.59.14.jpeg",
        "instances": [{"pts": [[500, 450]], "lbs": [1]}],
    },
    {
        "stratum": "facil", "qid": "facil_06_oscarina", "cow": "OSCARINA",
        "path": FIELD / "WhatsApp Image 2026-06-05 at 07.59.30.jpeg",
        "instances": [{"pts": [[580, 500]], "lbs": [1]}],
    },
    {
        "stratum": "facil", "qid": "facil_07_cristy", "cow": "CRISTY",
        "path": FIELD / "WhatsApp Image 2026-06-05 at 07.59.47.jpeg",
        "instances": [{"pts": [[580, 500]], "lbs": [1]}],
    },
    {
        "stratum": "facil", "qid": "facil_08_selena", "cow": "SELENA",
        "path": FIELD / "WhatsApp Image 2026-06-05 at 08.00.07.jpeg",
        "instances": [{"pts": [[580, 500]], "lbs": [1]}],
    },
    {
        "stratum": "facil", "qid": "facil_09_nohelia", "cow": "NOHELIA",
        "path": FIELD / "WhatsApp Image 2026-06-05 at 08.00.21.jpeg",
        "instances": [{"pts": [[580, 500]], "lbs": [1]}],
    },
    {
        "stratum": "facil", "qid": "facil_10_martinica", "cow": "MARTINICA",
        "path": FIELD / "WhatsApp Image 2026-06-05 at 08.00.48.jpeg",
        "instances": [{"pts": [[550, 500]], "lbs": [1]}],
    },
    {
        "stratum": "facil", "qid": "facil_11_ford", "cow": "FORD",
        "path": FIELD / "WhatsApp Image 2026-06-05 at 08.01.11.jpeg",
        "instances": [{"pts": [[580, 500]], "lbs": [1]}],
    },
    {
        "stratum": "facil", "qid": "facil_12_zafiro", "cow": "ZAFIRO",
        "path": FIELD / "WhatsApp Image 2026-06-05 at 08.01.27.jpeg",
        "instances": [{"pts": [[580, 500]], "lbs": [1]}],
    },
    {
        "stratum": "facil", "qid": "facil_13_chiquita", "cow": "CHIQUITA",
        "path": FIELD / "WhatsApp Image 2026-06-05 at 08.01.47.jpeg",
        "instances": [{"pts": [[580, 500]], "lbs": [1]}],
    },
    {
        "stratum": "facil", "qid": "facil_14_nohemi", "cow": "NOHEMI",
        "path": FIELD / "WhatsApp Image 2026-06-05 at 08.02.08.jpeg",
        "instances": [{"pts": [[580, 500]], "lbs": [1]}],
    },
    {
        "stratum": "facil", "qid": "facil_15_karina", "cow": "KARINA",
        "path": FIELD / "WhatsApp Image 2026-06-05 at 08.02.30.jpeg",
        "instances": [{"pts": [[580, 500]], "lbs": [1]}],
    },

    # ==================== 15 MEDIAS (Ráfagas dinámicas y repesaje) ====================
    {
        "stratum": "media", "qid": "media_01_ambar_burst1", "cow": "AMBAR",
        "path": GROUPED / "6699" / "IMG_20260604_064714.jpg",
        "instances": [{"pts": [[2048, 1152]], "lbs": [1]}],
    },
    {
        "stratum": "media", "qid": "media_02_ambar_burst2", "cow": "AMBAR",
        "path": GROUPED / "6699" / "IMG_20260604_064716.jpg",
        "instances": [{"pts": [[2048, 1152]], "lbs": [1]}],
    },
    {
        "stratum": "media", "qid": "media_03_ambar_burst3", "cow": "AMBAR",
        "path": GROUPED / "6699" / "IMG_20260604_064722.jpg",
        "instances": [{"pts": [[2048, 1152]], "lbs": [1]}],
    },
    {
        "stratum": "media", "qid": "media_04_estrellita_burst1", "cow": "ESTRELLITA",
        "path": GROUPED / "7260" / "IMG_20260604_064949.jpg",
        "instances": [{"pts": [[2048, 1152]], "lbs": [1]}],
    },
    {
        "stratum": "media", "qid": "media_05_estrellita_burst2", "cow": "ESTRELLITA",
        "path": GROUPED / "7260" / "IMG_20260604_064955.jpg",
        "instances": [{"pts": [[2048, 1152]], "lbs": [1]}],
    },
    {
        "stratum": "media", "qid": "media_06_estrellita_burst3", "cow": "ESTRELLITA",
        "path": GROUPED / "7260" / "IMG_20260604_064958.jpg",
        "instances": [{"pts": [[2048, 1152]], "lbs": [1]}],
    },
    {
        "stratum": "media", "qid": "media_07_taty_burst1", "cow": "TATY",
        "path": GROUPED / "6705" / "IMG_20260604_070123.jpg",
        "instances": [{"pts": [[2048, 1152]], "lbs": [1]}],
    },
    {
        "stratum": "media", "qid": "media_08_taty_burst2", "cow": "TATY",
        "path": GROUPED / "6705" / "IMG_20260604_070128.jpg",
        "instances": [{"pts": [[2048, 1152]], "lbs": [1]}],
    },
    {
        "stratum": "media", "qid": "media_09_nahomi_burst1", "cow": "NAHOMI",
        "path": GROUPED / "3683" / "IMG_20260604_064257.jpg",
        "instances": [{"pts": [[2048, 1152]], "lbs": [1]}],
    },
    {
        "stratum": "media", "qid": "media_10_nahomi_burst2", "cow": "NAHOMI",
        "path": GROUPED / "3683" / "IMG_20260604_064259.jpg",
        "instances": [{"pts": [[2048, 1152]], "lbs": [1]}],
    },
    {
        "stratum": "media", "qid": "media_11_karina_burst1", "cow": "KARINA",
        "path": GROUPED / "6703_3" / "IMG_20260604_064052.jpg",
        "instances": [{"pts": [[2048, 1152]], "lbs": [1]}],
    },
    {
        "stratum": "media", "qid": "media_12_karina_burst2", "cow": "KARINA",
        "path": GROUPED / "6703_3" / "IMG_20260604_064055.jpg",
        "instances": [{"pts": [[2048, 1152]], "lbs": [1]}],
    },
    {
        "stratum": "media", "qid": "media_13_odra_burst1", "cow": "ODRA",
        "path": GROUPED / "3159" / "IMG_20260604_065125.jpg",
        "instances": [{"pts": [[2048, 1152]], "lbs": [1]}],
    },
    {
        "stratum": "media", "qid": "media_14_anita_repesaje", "cow": "ANITA",
        "path": REPESAJE / "anita.jpeg",
        "instances": [{"pts": [[640, 480]], "lbs": [1]}],
    },
    {
        "stratum": "media", "qid": "media_15_damita_repesaje", "cow": "DAMITA",
        "path": REPESAJE / "damita.jpeg",
        "instances": [{"pts": [[800, 600]], "lbs": [1]}],
    },

    # ==================== 10 DIFÍCILES (Casos límite, oclusiones, multi-vaca) ====================
    {
        "stratum": "dificil", "qid": "dificil_01_karina_missed", "cow": "KARINA",
        "path": REPESAJE / "karina.jpeg",
        "instances": [{"pts": [[634, 646], [1480, 600]], "lbs": [1, 0]}],
    },
    {
        "stratum": "dificil", "qid": "dificil_02_oscarina_missed", "cow": "OSCARINA",
        "path": REPESAJE / "oscarina.jpeg",
        "instances": [{"pts": [[632, 697], [1450, 600]], "lbs": [1, 0]}],
    },
    {
        "stratum": "dificil", "qid": "dificil_03_diagira_multi3", "cow": "DIAGIRA",
        "path": REPESAJE / "diagira.jpeg",
        "instances": [
            {"pts": [[654, 658], [1400, 500]], "lbs": [1, 0]}, # vaca primer plano
            {"pts": [[1000, 450]], "lbs": [1]},               # vaca fondo
        ],
    },
    {
        "stratum": "dificil", "qid": "dificil_04_lubianca_multi2", "cow": "LUBIANCA",
        "path": REPESAJE / "lubianca.jpeg",
        "instances": [
            {"pts": [[519, 503]], "lbs": [1]},                # vaca primer plano
            {"pts": [[991, 343]], "lbs": [1]},                # vaca fondo derecha
        ],
    },
    {
        "stratum": "dificil", "qid": "dificil_05_mafer_multi", "cow": "MAFER",
        "path": REPESAJE / "mafer.jpeg",
        "instances": [
            {"pts": [[702, 728]], "lbs": [1]},                # vaca primer plano
            {"pts": [[81, 509]], "lbs": [1]},                 # vaca lateral izquierda
        ],
    },
    {
        "stratum": "dificil", "qid": "dificil_06_chaparrita_occlusion", "cow": "CHAPARRITA",
        "path": REPESAJE / "chaparrita.jpeg",
        "instances": [
            {"pts": [[510, 559]], "lbs": [1]},                # vaca principal
            {"pts": [[963, 403]], "lbs": [1]},                # vaca trasera
        ],
    },
    {
        "stratum": "dificil", "qid": "dificil_07_zafiro_multi2", "cow": "ZAFIRO",
        "path": REPESAJE / "zafiro.jpeg",
        "instances": [
            {"pts": [[475, 531]], "lbs": [1]},                # vaca primer plano
            {"pts": [[951, 387]], "lbs": [1]},                # vaca fondo
        ],
    },
    {
        "stratum": "dificil", "qid": "dificil_08_selena_multi2", "cow": "SELENA",
        "path": REPESAJE / "selena.jpeg",
        "instances": [
            {"pts": [[520, 532]], "lbs": [1]},                # vaca primer plano
        ],
    },
    {
        "stratum": "dificil", "qid": "dificil_09_nohemi_multi2", "cow": "NOHEMI",
        "path": REPESAJE / "nohemi.jpeg",
        "instances": [
            {"pts": [[563, 543]], "lbs": [1]},                # vaca primer plano
        ],
    },
    {
        "stratum": "dificil", "qid": "dificil_10_mariquita_multi2", "cow": "MARIQUITA",
        "path": REPESAJE / "mariquita.jpeg",
        "instances": [
            {"pts": [[564, 526]], "lbs": [1]},                # vaca primer plano
        ],
    },
]


def main():
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    for sub in ("images", "labels", "masks", "overlays"):
        (OUT_DIR / sub).mkdir(parents=True, exist_ok=True)

    sam = SAM("mobile_sam.pt")
    manifest_rows = []

    print(f"Generando conjunto de validación limpio en {OUT_DIR} ({len(QUEUE_SPEC)} imágenes)...")

    for item in QUEUE_SPEC:
        stratum = item["stratum"]
        qid = item["qid"]
        cow = item["cow"]
        src_path = item["path"]
        assert src_path.exists(), f"No existe {src_path}"

        img = cv2.imread(str(src_path))
        assert img is not None, f"No se pudo leer {src_path}"
        H, W = img.shape[:2]

        dest_img = OUT_DIR / "images" / f"{qid}{src_path.suffix}"
        shutil.copy(src_path, dest_img)

        label_lines = []
        overlay = img.copy()
        inst_count = 0

        for idx, inst_spec in enumerate(item["instances"]):
            pts = inst_spec["pts"]
            lbs = inst_spec["lbs"]
            r = sam(str(src_path), points=[pts], labels=[lbs], verbose=False)
            if not r or r[0].masks is None or len(r[0].masks.data) == 0:
                print(f"  ALERTA: SAM no segmentó instancia {idx} en {qid}")
                continue
            mask = (r[0].masks.data[0].cpu().numpy() * 255).astype(np.uint8)
            if mask.shape[:2] != (H, W):
                mask = cv2.resize(mask, (W, H), interpolation=cv2.INTER_NEAREST)

            # Guardar máscara PNG
            mask_path = OUT_DIR / "masks" / f"{qid}_inst{idx}.png"
            cv2.imwrite(str(mask_path), mask)

            # Extraer polígono normalizado
            poly = mask_to_polygon(mask, W, H)
            if poly is not None:
                label_lines.append("0 " + " ".join(map(str, poly)))
                inst_count += 1

            # Overlay visual
            col = np.zeros_like(overlay)
            c_rgb = COLORS[idx % len(COLORS)]
            col[mask > 0] = c_rgb
            overlay = cv2.addWeighted(overlay, 1.0, col, 0.45, 0)
            cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(overlay, cnts, -1, (255, 255, 255), 2)

        # Guardar label .txt
        label_path = OUT_DIR / "labels" / f"{qid}.txt"
        label_path.write_text("\n".join(label_lines) + ("\n" if label_lines else ""))

        # Guardar overlay de verificación
        ov_path = OUT_DIR / "overlays" / f"{qid}.jpg"
        cv2.imwrite(str(ov_path), overlay)

        manifest_rows.append({
            "qid": qid,
            "stratum": stratum,
            "cow_id": cow,
            "source_file": src_path.name,
            "image_file": dest_img.name,
            "n_instances": inst_count,
            "width": W,
            "height": H,
            "status": "validado_sam",
        })
        print(f"  ✓ [{stratum:7}] {qid:28} | Vaca: {cow:12} | {inst_count} instancias")

    # Escribir manifest.csv
    manifest_csv = OUT_DIR / "manifest.csv"
    with open(manifest_csv, "w", newline="") as f:
        fields = ["qid", "stratum", "cow_id", "source_file", "image_file", "n_instances", "width", "height", "status"]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(manifest_rows)

    print(f"\n✓ Dataset de validación limpio generado exitosamente.")
    print(f"Total: {len(manifest_rows)} imágenes ({sum(r['n_instances'] for r in manifest_rows)} instancias totales)")
    print(f"Manifiesto: {manifest_csv}")


if __name__ == "__main__":
    raise SystemExit(main())
