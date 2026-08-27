"""Herramienta de anotación asistida con MobileSAM para el conjunto de validación limpio (~40 imágenes estratificadas).

Soporta múltiples instancias por foto (cada vaca = una instancia separada).
Genera formato YOLO-seg (labels .txt normalizados) y máscaras binarias (.png).

Uso:
    python3 src/annotate_val.py
    python3 src/annotate_val.py --auto-assist    # Inicializa candidatos con SAM para revisión rápida
    python3 src/annotate_val.py --status         # Muestra estado de la cola
"""
from __future__ import annotations
import argparse, csv, sys
from pathlib import Path
import cv2
import numpy as np
from ultralytics import SAM

ROOT = Path(__file__).resolve().parent.parent
FIELD = ROOT / "data" / "field"
GROUPED = Path("/home/luisc/Documents/Thesis_final_raw/raw/_grouped")
REPESAJE = FIELD / "repesaje_1206"
OUT_DIR = ROOT / "data" / "val_clean"

QUEUE = [
    # 15 Fáciles (laterales controladas 5/06)
    ("facil", "5_06_perla", FIELD / "WhatsApp Image 2026-06-05 at 07.57.46.jpeg", "PERLA"),
    ("facil", "5_06_odra", FIELD / "WhatsApp Image 2026-06-05 at 07.58.08.jpeg", "ODRA"),
    ("facil", "5_06_mariquita", FIELD / "WhatsApp Image 2026-06-05 at 07.58.33.jpeg", "MARIQUITA"),
    ("facil", "5_06_martita", FIELD / "WhatsApp Image 2026-06-05 at 07.58.52.jpeg", "MARTITA"),
    ("facil", "5_06_lubianca", FIELD / "WhatsApp Image 2026-06-05 at 07.59.14.jpeg", "LUBIANCA"),
    ("facil", "5_06_oscarina", FIELD / "WhatsApp Image 2026-06-05 at 07.59.30.jpeg", "OSCARINA"),
    ("facil", "5_06_cristy", FIELD / "WhatsApp Image 2026-06-05 at 07.59.47.jpeg", "CRISTY"),
    ("facil", "5_06_selena", FIELD / "WhatsApp Image 2026-06-05 at 08.00.07.jpeg", "SELENA"),
    ("facil", "5_06_nohelia", FIELD / "WhatsApp Image 2026-06-05 at 08.00.21.jpeg", "NOHELIA"),
    ("facil", "5_06_martinica", FIELD / "WhatsApp Image 2026-06-05 at 08.00.48.jpeg", "MARTINICA"),
    ("facil", "5_06_ford", FIELD / "WhatsApp Image 2026-06-05 at 08.01.11.jpeg", "FORD"),
    ("facil", "5_06_zafiro", FIELD / "WhatsApp Image 2026-06-05 at 08.01.27.jpeg", "ZAFIRO"),
    ("facil", "5_06_chiquita", FIELD / "WhatsApp Image 2026-06-05 at 08.01.47.jpeg", "CHIQUITA"),
    ("facil", "5_06_nohemi", FIELD / "WhatsApp Image 2026-06-05 at 08.02.08.jpeg", "NOHEMI"),
    ("facil", "5_06_karina", FIELD / "WhatsApp Image 2026-06-05 at 08.02.30.jpeg", "KARINA"),

    # 15 Medias (ráfagas y repesaje 12/06)
    ("media", "burst_ambar_01", GROUPED / "6699" / "IMG_20260604_064714.jpg", "AMBAR"),
    ("media", "burst_ambar_02", GROUPED / "6699" / "IMG_20260604_064716.jpg", "AMBAR"),
    ("media", "burst_ambar_03", GROUPED / "6699" / "IMG_20260604_064722.jpg", "AMBAR"),
    ("media", "burst_estrellita_01", GROUPED / "7260" / "IMG_20260604_064949.jpg", "ESTRELLITA"),
    ("media", "burst_estrellita_02", GROUPED / "7260" / "IMG_20260604_064955.jpg", "ESTRELLITA"),
    ("media", "burst_estrellita_03", GROUPED / "7260" / "IMG_20260604_064958.jpg", "ESTRELLITA"),
    ("media", "burst_taty_01", GROUPED / "6705" / "IMG_20260604_070123.jpg", "TATY"),
    ("media", "burst_taty_02", GROUPED / "6705" / "IMG_20260604_070128.jpg", "TATY"),
    ("media", "burst_nahomi_01", GROUPED / "3683" / "IMG_20260604_064257.jpg", "NAHOMI"),
    ("media", "burst_nahomi_02", GROUPED / "3683" / "IMG_20260604_064259.jpg", "NAHOMI"),
    ("media", "burst_karina_01", GROUPED / "6703_3" / "IMG_20260604_064052.jpg", "KARINA"),
    ("media", "burst_karina_02", GROUPED / "6703_3" / "IMG_20260604_064055.jpg", "KARINA"),
    ("media", "burst_odra_01", GROUPED / "3159" / "IMG_20260604_065125.jpg", "ODRA"),
    ("media", "12_06_anita", REPESAJE / "anita.jpeg", "ANITA"),
    ("media", "12_06_damita", REPESAJE / "damita.jpeg", "DAMITA"),

    # 10 Difíciles (casos límite, solapes, oclusiones, karina/oscarina)
    ("dificil", "12_06_karina", REPESAJE / "karina.jpeg", "KARINA"),
    ("dificil", "12_06_oscarina", REPESAJE / "oscarina.jpeg", "OSCARINA"),
    ("dificil", "12_06_diagira", REPESAJE / "diagira.jpeg", "DIAGIRA"),
    ("dificil", "12_06_lubianca", REPESAJE / "lubianca.jpeg", "LUBIANCA"),
    ("dificil", "12_06_mafer", REPESAJE / "mafer.jpeg", "MAFER"),
    ("dificil", "12_06_chaparrita", REPESAJE / "chaparrita.jpeg", "CHAPARRITA"),
    ("dificil", "12_06_zafiro", REPESAJE / "zafiro.jpeg", "ZAFIRO"),
    ("dificil", "12_06_selena", REPESAJE / "selena.jpeg", "SELENA"),
    ("dificil", "12_06_nohemi", REPESAJE / "nohemi.jpeg", "NOHEMI"),
    ("dificil", "12_06_mariquita", REPESAJE / "mariquita.jpeg", "MARIQUITA"),
]

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
    """Extrae contorno mayor -> lista de puntos normalizados [x1, y1, ...]."""
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


def run_sam(sam: SAM, img: np.ndarray, pts: list, labels: list) -> np.ndarray | None:
    if not pts:
        return None
    r = sam(img, points=[pts], labels=[labels], verbose=False)
    if not r or r[0].masks is None or len(r[0].masks.data) == 0:
        return None
    return r[0].masks.data[0].cpu().numpy().astype(np.uint8)


def render_display(base: np.ndarray, scale: float, completed_instances: list[np.ndarray],
                   curr_mask: np.ndarray | None, pts: list, labels: list,
                   header_text: str) -> np.ndarray:
    dh, dw = base.shape[:2]
    d2 = base.copy()

    # Instancias ya completadas
    for idx, inst in enumerate(completed_instances):
        m = cv2.resize(inst, (dw, dh), interpolation=cv2.INTER_NEAREST)
        col = np.zeros_like(d2)
        c_rgb = COLORS[(idx + 1) % len(COLORS)]
        col[m > 0] = c_rgb
        d2 = cv2.addWeighted(d2, 1.0, col, 0.45, 0)
        # Borde
        cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(d2, cnts, -1, c_rgb, 2)

    # Instancia actual en edición
    if curr_mask is not None:
        m = cv2.resize(curr_mask, (dw, dh), interpolation=cv2.INTER_NEAREST)
        col = np.zeros_like(d2)
        col[m > 0] = COLORS[0]
        d2 = cv2.addWeighted(d2, 1.0, col, 0.5, 0)
        cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(d2, cnts, -1, (255, 255, 255), 2)

    # Puntos de click
    for (x, y), lb in zip(pts, labels):
        cx, cy = int(x * scale), int(y * scale)
        color = (0, 255, 0) if lb == 1 else (0, 0, 255)
        cv2.circle(d2, (cx, cy), 6, color, -1)
        cv2.circle(d2, (cx, cy), 8, (255, 255, 255), 1)

    # Barra de estado superior
    cv2.rectangle(d2, (0, 0), (dw, 60), (20, 20, 20), -1)
    cv2.putText(d2, header_text, (12, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)
    cv2.putText(d2, "Click Izq: +Vaca | Click Der: -Fondo | n: Siguiente vaca en foto | ENTER: Guardar foto | z: Undo | q: Salir",
                (12, 48), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (200, 200, 200), 1)
    return d2


def save_photo_annotations(qid: str, stratum: str, cow_id: str, src_path: Path,
                           instances: list[np.ndarray], out_dir: Path) -> dict:
    (out_dir / "images").mkdir(parents=True, exist_ok=True)
    (out_dir / "labels").mkdir(parents=True, exist_ok=True)
    (out_dir / "masks").mkdir(parents=True, exist_ok=True)
    (out_dir / "overlays").mkdir(parents=True, exist_ok=True)

    img = cv2.imread(str(src_path))
    assert img is not None
    H, W = img.shape[:2]

    # Guardar imagen con nombre estandarizado
    dest_img = out_dir / "images" / f"{qid}{src_path.suffix}"
    import shutil
    shutil.copy(src_path, dest_img)

    # Guardar labels YOLO-seg y máscaras binarias
    label_lines = []
    overlay = img.copy()

    for idx, mask in enumerate(instances):
        if mask.shape[:2] != (H, W):
            mask = cv2.resize(mask, (W, H), interpolation=cv2.INTER_NEAREST)
        # Guardar máscara binaria PNG
        mask_path = out_dir / "masks" / f"{qid}_inst{idx}.png"
        cv2.imwrite(str(mask_path), mask * 255)

        # Polígono YOLO
        poly = mask_to_polygon(mask, W, H)
        if poly is not None:
            label_lines.append("0 " + " ".join(map(str, poly)))

        # Overlay visual
        col = np.zeros_like(overlay)
        col[mask > 0] = COLORS[idx % len(COLORS)]
        overlay = cv2.addWeighted(overlay, 1.0, col, 0.45, 0)
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(overlay, cnts, -1, (255, 255, 255), 2)

    # Escribir label .txt
    label_path = out_dir / "labels" / f"{qid}.txt"
    label_path.write_text("\n".join(label_lines) + ("\n" if label_lines else ""))

    # Guardar overlay de verificación
    ov_path = out_dir / "overlays" / f"{qid}.jpg"
    cv2.imwrite(str(ov_path), overlay)

    return {
        "qid": qid,
        "stratum": stratum,
        "cow_id": cow_id,
        "source_file": src_path.name,
        "image_file": dest_img.name,
        "n_instances": len(instances),
        "n_polygons": len(label_lines),
        "status": "anotado",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sam-model", default="mobile_sam.pt")
    ap.add_argument("--out-dir", default=str(OUT_DIR))
    ap.add_argument("--status", action="store_true", help="Mostrar resumen de avance")
    ap.add_argument("--auto-assist", action="store_true", help="Precarga propuestas SAM con detector para acelerar")
    ap.add_argument("--redo", action="store_true", help="Reanotar desde el inicio")
    ap.add_argument("--max-width", type=int, default=1280)
    ap.add_argument("--max-height", type=int, default=850)
    a = ap.parse_args()

    out_dir = Path(a.out_dir)
    manifest_csv = out_dir / "manifest.csv"

    # Cargar progreso previo
    manifest: dict[str, dict] = {}
    if manifest_csv.exists() and not a.redo:
        with open(manifest_csv, newline="") as f:
            for r in csv.DictReader(f):
                manifest[r["qid"]] = r

    if a.status:
        n_done = sum(1 for q in QUEUE if q[1] in manifest)
        print(f"\n=== ESTADO SET DE VALIDACIÓN ===")
        print(f"Total imágenes: {len(QUEUE)} | Anotadas: {n_done}/{len(QUEUE)}")
        by_strat = {}
        for s, qid, _, cow in QUEUE:
            by_strat.setdefault(s, {"done": 0, "total": 0})
            by_strat[s]["total"] += 1
            if qid in manifest:
                by_strat[s]["done"] += 1
        for s, d in by_strat.items():
            print(f"  {s:10}: {d['done']:2d}/{d['total']:2d}")
        return 0

    print(f"\nInicializando MobileSAM ({a.sam_model})...")
    sam = SAM(a.sam_model)

    cv2.namedWindow("Anotacion_Val_Set", cv2.WINDOW_NORMAL)

    idx = 0
    while idx < len(QUEUE):
        stratum, qid, src_path, cow = QUEUE[idx]
        if qid in manifest and not a.redo:
            print(f"[{idx+1}/{len(QUEUE)}] {qid} ya anotado. Saltando (usa --redo para rehacer).")
            idx += 1
            continue

        full = cv2.imread(str(src_path))
        if full is None:
            print(f"Error al leer {src_path}")
            idx += 1
            continue

        H, W = full.shape[:2]
        sc = min(1.0, a.max_width / W, a.max_height / H)
        disp_base = cv2.resize(full, (int(W * sc), int(H * sc)))

        instances: list[np.ndarray] = []
        curr_pts: list = []
        curr_labels: list = []
        curr_mask: np.ndarray | None = None

        # Si se solicita auto-assist, precargar click central en vaca
        if a.auto_assist:
            # Centro de la imagen como click positivo inicial
            curr_pts.append([W / 2.0, H / 2.0])
            curr_labels.append(1)
            curr_mask = run_sam(sam, full, curr_pts, curr_labels)

        def update_render():
            header = f"[{idx+1}/{len(QUEUE)}] {qid} | Estrato: {stratum.upper()} | Vaca: {cow} | Instancias: {len(instances)} (editando #{len(instances)+1})"
            d = render_display(disp_base, sc, instances, curr_mask, curr_pts, curr_labels, header)
            cv2.imshow("Anotacion_Val_Set", d)

        def on_mouse(event, x, y, flags, _):
            nonlocal curr_mask
            if event == cv2.EVENT_LBUTTONDOWN:
                curr_pts.append([x / sc, y / sc])
                curr_labels.append(1)
            elif event == cv2.EVENT_RBUTTONDOWN:
                curr_pts.append([x / sc, y / sc])
                curr_labels.append(0)
            else:
                return
            curr_mask = run_sam(sam, full, curr_pts, curr_labels)
            update_render()

        cv2.setMouseCallback("Anotacion_Val_Set", on_mouse)
        update_render()

        action = None
        while True:
            k = cv2.waitKey(20) & 0xFF
            if k in (13, 10, 32):  # ENTER o ESPACIO -> Guardar foto
                if curr_mask is not None:
                    instances.append(curr_mask)
                action = "accept"
                break
            elif k in (ord("n"), ord("a")):  # Siguiente instancia de vaca en misma foto
                if curr_mask is not None:
                    instances.append(curr_mask)
                    curr_pts = []
                    curr_labels = []
                    curr_mask = None
                    print(f"  Instancia #{len(instances)} agregada. Listo para la siguiente vaca.")
                    update_render()
            elif k in (ord("z"), 8):  # Undo
                if curr_pts:
                    curr_pts.pop()
                    curr_labels.pop()
                    curr_mask = run_sam(sam, full, curr_pts, curr_labels) if curr_pts else None
                    update_render()
            elif k == ord("r"):  # Reset instancia actual
                curr_pts = []
                curr_labels = []
                curr_mask = None
                update_render()
            elif k == ord("s"):  # Skip
                action = "skip"
                break
            elif k == ord("b"):  # Back
                action = "back"
                break
            elif k == ord("q"):  # Quit
                action = "quit"
                break

        if action == "quit":
            break
        elif action == "back":
            idx = max(0, idx - 1)
            continue
        elif action == "skip":
            print(f"  {qid}: saltado")
            idx += 1
            continue
        elif action == "accept":
            if not instances:
                print(f"  {qid}: sin máscaras, saltado")
                idx += 1
                continue
            res = save_photo_annotations(qid, stratum, cow, src_path, instances, out_dir)
            manifest[qid] = res
            # Guardar manifest incremental
            with open(manifest_csv, "w", newline="") as f:
                fields = ["qid", "stratum", "cow_id", "source_file", "image_file", "n_instances", "n_polygons", "status"]
                w = csv.DictWriter(f, fieldnames=fields)
                w.writeheader()
                for item in manifest.values():
                    w.writerow(item)
            print(f"  ✓ {qid} ({stratum}): {len(instances)} instancia(s) guardada(s)")
            idx += 1

    cv2.destroyAllWindows()
    print(f"\nSesión finalizada. Total anotadas: {len(manifest)}/{len(QUEUE)}")
    print(f"Manifiesto -> {manifest_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
