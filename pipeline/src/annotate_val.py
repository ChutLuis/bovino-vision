"""Herramienta de anotación HÍBRIDA (MobileSAM + Pincel/Borrador fluido con Zoom).

Soluciona:
- Menú contextual de Qt desactivado (WINDOW_GUI_NORMAL).
- Alternativa de Borrador con tecla 'e' o Shift + Click Izquierdo.
- Sin bloqueos: renderizado eficiente.
- Zoom hasta 8x con rueda del ratón y paneo fluido.
"""
from __future__ import annotations
import argparse, csv, sys
from pathlib import Path
import cv2
import numpy as np
from ultralytics import SAM

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_yolo_seg_dataset import resolve_grouped  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FIELD = ROOT / "data" / "field"
# Ráfagas crudas: $BOVINO_RAW_GROUPED, data/field/raw/_grouped o ~/Documents/Thesis_final_raw/raw/_grouped
GROUPED = resolve_grouped(None, strict=False)
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
    (0, 230, 255),   # Amarillo/dorado (instancia activa)
    (0, 255, 100),   # Verde
    (255, 120, 0),   # Azul
    (200, 0, 255),   # Magenta
    (0, 165, 255),   # Naranja
    (255, 255, 0),   # Cyan
]

ARROWS = {
    63232: (0, -1), 63233: (0, 1), 63234: (-1, 0), 63235: (1, 0),
    65362: (0, -1), 65364: (0, 1), 65361: (-1, 0), 65363: (1, 0),
    ord("w"): (0, -1), ord("s"): (0, 1), ord("a"): (-1, 0), ord("d"): (1, 0)
}

MIN_AREA_FRAC = 0.005


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def wheel_delta(flags):
    try:
        return cv2.getMouseWheelDelta(flags)
    except AttributeError:
        raw = (int(flags) >> 16) & 0xFFFF
        return raw - 65536 if raw > 32767 else raw


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


def run_sam(sam: SAM, img: np.ndarray, pts: list, labels: list) -> np.ndarray | None:
    if not pts:
        return None
    r = sam(img, points=[pts], labels=[labels], verbose=False)
    if not r or r[0].masks is None or len(r[0].masks.data) == 0:
        return None
    return r[0].masks.data[0].cpu().numpy().astype(np.uint8)


def save_photo_annotations(qid: str, stratum: str, cow_id: str, src_path: Path,
                           instances: list[np.ndarray], out_dir: Path) -> dict:
    (out_dir / "images").mkdir(parents=True, exist_ok=True)
    (out_dir / "labels").mkdir(parents=True, exist_ok=True)
    (out_dir / "masks").mkdir(parents=True, exist_ok=True)
    (out_dir / "overlays").mkdir(parents=True, exist_ok=True)

    img = cv2.imread(str(src_path))
    assert img is not None
    H, W = img.shape[:2]

    dest_img = out_dir / "images" / f"{qid}{src_path.suffix}"
    import shutil
    shutil.copy(src_path, dest_img)

    label_lines = []
    overlay = img.copy()

    for idx, mask in enumerate(instances):
        if mask.shape[:2] != (H, W):
            mask = cv2.resize(mask, (W, H), interpolation=cv2.INTER_NEAREST)
        mask_bin = (mask > 0).astype(np.uint8)

        # Guardar PNG
        cv2.imwrite(str(out_dir / "masks" / f"{qid}_inst{idx}.png"), mask_bin * 255)

        # Polígono YOLO
        poly = mask_to_polygon(mask_bin, W, H)
        if poly is not None:
            label_lines.append("0 " + " ".join(map(str, poly)))

        # Overlay visual
        col = np.zeros_like(overlay)
        col[mask_bin > 0] = COLORS[(idx + 1) % len(COLORS)]
        overlay = cv2.addWeighted(overlay, 1.0, col, 0.45, 0)
        cnts, _ = cv2.findContours(mask_bin, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(overlay, cnts, -1, (255, 255, 255), 2)

    (out_dir / "labels" / f"{qid}.txt").write_text("\n".join(label_lines) + ("\n" if label_lines else ""))
    cv2.imwrite(str(out_dir / "overlays" / f"{qid}.jpg"), overlay)

    return {
        "qid": qid,
        "stratum": stratum,
        "cow_id": cow_id,
        "source_file": src_path.name,
        "image_file": dest_img.name,
        "n_instances": len(instances),
        "n_polygons": len(label_lines),
        "status": "anotado_manual",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sam-model", default="mobile_sam.pt")
    ap.add_argument("--out-dir", default=str(OUT_DIR))
    ap.add_argument("--status", action="store_true", help="Mostrar resumen de avance")
    ap.add_argument("--redo", action="store_true", help="Reanotar desde el inicio")
    ap.add_argument("--max-width", type=int, default=1280)
    ap.add_argument("--max-height", type=int, default=800)
    a = ap.parse_args()

    out_dir = Path(a.out_dir)
    manifest_csv = out_dir / "manifest.csv"

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

    # Desactivar barra/menú contextual y paneo automático de Qt
    cv2.namedWindow("Anotacion_Val_Set", cv2.WINDOW_AUTOSIZE | cv2.WINDOW_GUI_NORMAL)

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
        dw, dh = int(W * sc), int(H * sc)
        disp_base = cv2.resize(full, (dw, dh))

        instances: list[np.ndarray] = []
        sam_pts: list = []
        sam_lbs: list = []

        current_mask = np.zeros((dh, dw), dtype=np.uint8)
        undo_stack: list[np.ndarray] = []

        state = {
            "mode": "sam",        # "sam" o "paint"
            "tool": "pincel",     # "pincel" o "borrador" (para modo paint)
            "zoom": 1.0,
            "ox": 0.0,
            "oy": 0.0,
            "brush": 22,
            "drawing": 0,         # 0=no, 1=pintar, 2=borrar
            "last_base_pos": None,
            "cur_pos": (0, 0),
            "show_overlay": True,
            "panning": None,
        }

        def get_viewport():
            vw = dw / state["zoom"]
            vh = dh / state["zoom"]
            state["ox"] = clamp(state["ox"], 0, dw - vw)
            state["oy"] = clamp(state["oy"], 0, dh - vh)
            return vw, vh

        def win_to_base(wx, wy):
            vw, vh = get_viewport()
            bx = state["ox"] + wx * vw / dw
            by = state["oy"] + wy * vh / dh
            return int(round(bx)), int(round(by))

        def apply_paint_stroke(bx, by, val):
            r = int(round(state["brush"] / state["zoom"]))
            r = max(1, r)
            if state["last_base_pos"] is not None:
                lx, ly = state["last_base_pos"]
                cv2.line(current_mask, (lx, ly), (bx, by), val, r * 2)
            cv2.circle(current_mask, (bx, by), r, val, -1)
            state["last_base_pos"] = (bx, by)

        def apply_zoom(wx, wy, factor):
            vw_old, vh_old = get_viewport()
            bx = state["ox"] + wx * vw_old / dw
            by = state["oy"] + wy * vh_old / dh

            state["zoom"] = clamp(state["zoom"] * factor, 1.0, 8.0)
            vw_new, vh_new = dw / state["zoom"], dh / state["zoom"]
            state["ox"] = bx - wx * vw_new / dw
            state["oy"] = by - wy * vh_new / dh
            get_viewport()

        def render():
            vw, vh = get_viewport()
            x0, y0 = int(state["ox"]), int(state["oy"])
            x1, y1 = min(dw, int(state["ox"] + vw)), min(dh, int(state["oy"] + vh))

            view = cv2.resize(disp_base[y0:y1, x0:x1], (dw, dh))

            # 1. Capa de instancias previas
            for i_idx, inst in enumerate(instances):
                m_disp = cv2.resize(inst, (dw, dh), interpolation=cv2.INTER_NEAREST)
                m_sub = cv2.resize(m_disp[y0:y1, x0:x1], (dw, dh), interpolation=cv2.INTER_NEAREST)
                mask_bool = m_sub > 0
                if mask_bool.any():
                    col = np.zeros_like(view)
                    c_rgb = COLORS[(i_idx + 1) % len(COLORS)]
                    col[mask_bool] = c_rgb
                    view = cv2.addWeighted(view, 1.0, col, 0.40, 0)

            # 2. Capa de máscara actual
            if state["show_overlay"] and current_mask.any():
                m_sub = cv2.resize(current_mask[y0:y1, x0:x1], (dw, dh), interpolation=cv2.INTER_NEAREST)
                mask_bool = m_sub > 0
                if mask_bool.any():
                    col = np.zeros_like(view)
                    col[mask_bool] = COLORS[0]
                    view = cv2.addWeighted(view, 1.0, col, 0.45, 0)

            # 3. Puntos SAM
            if state["mode"] == "sam":
                for (px, py), lb in zip(sam_pts, sam_lbs):
                    bdx, bdy = px * sc, py * sc
                    if x0 <= bdx <= x1 and y0 <= bdy <= y1:
                        wx = int((bdx - state["ox"]) * dw / vw)
                        wy = int((bdy - state["oy"]) * dh / vh)
                        color = (0, 255, 0) if lb == 1 else (0, 0, 255)
                        cv2.circle(view, (wx, wy), 6, color, -1)
                        cv2.circle(view, (wx, wy), 8, (255, 255, 255), 1)

            # 4. Indicador de pincel / borrador
            if state["mode"] == "paint":
                b_rad = max(2, int(state["brush"]))
                cur_color = (0, 255, 0) if state["tool"] == "pincel" else (0, 0, 255)
                cv2.circle(view, state["cur_pos"], b_rad, cur_color, 1)
                cv2.circle(view, state["cur_pos"], 1, (255, 255, 255), -1)

            # 5. Barra superior
            cv2.rectangle(view, (0, 0), (dw, 68), (20, 20, 20), -1)
            tool_str = "PINCEL (Izq: pintar, Der: borrar)" if state["tool"] == "pincel" else "BORRADOR (Izq: borrar, Der: pintar)"
            mode_badge = "[MODO SAM: Clicks]" if state["mode"] == "sam" else f"[MODO PAINT: {tool_str} r={state['brush']}px]"
            mode_color = (0, 255, 255) if state["mode"] == "sam" else (0, 255, 120)
            cv2.putText(view, f"[{idx+1}/{len(QUEUE)}] {qid} | {stratum.upper()} | Vaca: {cow} | Instancias: {len(instances)}",
                        (12, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.56, (255, 255, 255), 2)
            cv2.putText(view, f"{mode_badge}  (TAB/m: modo, e: alternar pincel/borrador)  Zoom: {state['zoom']:.1f}x",
                        (12, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.48, mode_color, 2)
            cv2.putText(view, "SAM: Izq=+Vaca, Der=-Fondo | PAINT: e=alternar herramienta, [/]=Tamano | n: Sig Vaca | ENTER: Guardar",
                        (12, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (190, 190, 190), 1)

            cv2.imshow("Anotacion_Val_Set", view)

        def on_mouse(event, x, y, flags, _):
            state["cur_pos"] = (x, y)
            shift_pressed = bool(flags & cv2.EVENT_FLAG_SHIFTKEY) or bool(flags & cv2.EVENT_FLAG_CTRLKEY)

            # Rueda de ratón -> Zoom
            if event == cv2.EVENT_MOUSEWHEEL:
                delta = wheel_delta(flags)
                apply_zoom(x, y, 1.25 if delta > 0 else 0.8)
                render()
                return

            # Botón central -> Pan
            if event == cv2.EVENT_MBUTTONDOWN:
                state["panning"] = (x, y)
                return
            if event == cv2.EVENT_MBUTTONUP:
                state["panning"] = None
                return

            # Movimiento de ratón
            if event == cv2.EVENT_MOUSEMOVE:
                l_down = bool(flags & cv2.EVENT_FLAG_LBUTTON)
                r_down = bool(flags & cv2.EVENT_FLAG_RBUTTON)
                if not l_down and not r_down and state["drawing"] != 0:
                    state["drawing"] = 0
                    state["last_base_pos"] = None

                if state["panning"] is not None:
                    vw, vh = get_viewport()
                    state["ox"] -= (x - state["panning"][0]) * vw / dw
                    state["oy"] -= (y - state["panning"][1]) * vh / dh
                    state["panning"] = (x, y)
                    render()
                    return
                elif state["mode"] == "paint" and state["drawing"]:
                    bx, by = win_to_base(x, y)
                    val = 1 if state["drawing"] == 1 else 0
                    apply_paint_stroke(bx, by, val)
                    render()
                    return
                elif state["mode"] == "paint":
                    render()
                    return

            # Clicks en MODO SAM
            if state["mode"] == "sam":
                if event == cv2.EVENT_LBUTTONDOWN or event == cv2.EVENT_RBUTTONDOWN:
                    if len(undo_stack) > 30:
                        undo_stack.pop(0)
                    undo_stack.append(current_mask.copy())

                    bx, by = win_to_base(x, y)
                    fx, fy = bx / sc, by / sc
                    # Click izq con Shift = negativo; Click der = negativo; Click izq = positivo
                    if event == cv2.EVENT_RBUTTONDOWN or (event == cv2.EVENT_LBUTTONDOWN and shift_pressed):
                        label = 0
                    else:
                        label = 1

                    sam_pts.append([fx, fy])
                    sam_lbs.append(label)

                    m = run_sam(sam, full, sam_pts, sam_lbs)
                    if m is not None:
                        current_mask[:] = cv2.resize(m, (dw, dh), interpolation=cv2.INTER_NEAREST)
                    render()
                return

            # Clicks / Arrastre en MODO PAINT
            if state["mode"] == "paint":
                if event == cv2.EVENT_LBUTTONDOWN:
                    if len(undo_stack) > 30:
                        undo_stack.pop(0)
                    undo_stack.append(current_mask.copy())

                    # Si tool es borrador o se presiona Shift -> borrar (val=0), sino pintar (val=1)
                    if state["tool"] == "borrador" or shift_pressed:
                        state["drawing"] = 2
                        val = 0
                    else:
                        state["drawing"] = 1
                        val = 1

                    state["last_base_pos"] = None
                    bx, by = win_to_base(x, y)
                    apply_paint_stroke(bx, by, val)
                    render()

                elif event == cv2.EVENT_RBUTTONDOWN:
                    if len(undo_stack) > 30:
                        undo_stack.pop(0)
                    undo_stack.append(current_mask.copy())

                    # Click derecho hace la acción opuesta a la herramienta activa
                    if state["tool"] == "borrador":
                        state["drawing"] = 1
                        val = 1
                    else:
                        state["drawing"] = 2
                        val = 0

                    state["last_base_pos"] = None
                    bx, by = win_to_base(x, y)
                    apply_paint_stroke(bx, by, val)
                    render()

                elif event in (cv2.EVENT_LBUTTONUP, cv2.EVENT_RBUTTONUP):
                    state["drawing"] = 0
                    state["last_base_pos"] = None
                    render()

        cv2.setMouseCallback("Anotacion_Val_Set", on_mouse)
        render()

        action = None
        while True:
            key = cv2.waitKeyEx(20)
            if key == -1:
                continue
            k = key & 0xFF

            # Enter / Espacio -> Aceptar foto
            if k in (13, 10, 32):
                if current_mask.any():
                    full_m = cv2.resize(current_mask, (W, H), interpolation=cv2.INTER_NEAREST)
                    instances.append(full_m)
                action = "accept"
                break

            # Cambiar modo SAM <-> PAINT (TAB, 'm', 'M', 'p', 'P')
            elif k in (9, ord("m"), ord("M"), ord("p"), ord("P")):
                state["mode"] = "paint" if state["mode"] == "sam" else "sam"
                state["drawing"] = 0
                state["last_base_pos"] = None
                render()

            # Alternar herramienta Pincel <-> Borrador ('e', 'E')
            elif k in (ord("e"), ord("E")):
                state["tool"] = "borrador" if state["tool"] == "pincel" else "pincel"
                print(f"  Herramienta activa: {state['tool'].upper()}")
                render()

            # Siguiente vaca en la misma foto ('n', 'N', 'a', 'A')
            elif k in (ord("n"), ord("N"), ord("a"), ord("A")):
                if current_mask.any():
                    full_m = cv2.resize(current_mask, (W, H), interpolation=cv2.INTER_NEAREST)
                    instances.append(full_m)
                    current_mask[:] = 0
                    sam_pts.clear()
                    sam_lbs.clear()
                    undo_stack.clear()
                    state["drawing"] = 0
                    state["last_base_pos"] = None
                    print(f"  ✓ Vaca #{len(instances)} guardada en esta foto. Listo para anotar la siguiente.")
                    render()

            # Undo ('z', 'Z' o Backspace)
            elif k in (ord("z"), ord("Z"), 8):
                if undo_stack:
                    current_mask[:] = undo_stack.pop()
                    if state["mode"] == "sam" and sam_pts:
                        sam_pts.pop()
                        sam_lbs.pop()
                    render()
                elif not current_mask.any() and instances:
                    # Si la máscara actual está vacía, recuperar la última vaca guardada
                    last_inst = instances.pop()
                    current_mask[:] = cv2.resize(last_inst, (dw, dh), interpolation=cv2.INTER_NEAREST)
                    print(f"  Deshecho: vaca #{len(instances)+1} recuperada para edición.")
                    render()

            # Tamaño de brocha ('[' y ']')
            elif k == ord("]"):
                state["brush"] = min(120, state["brush"] + 4)
                render()
            elif k == ord("["):
                state["brush"] = max(2, state["brush"] - 4)
                render()

            # Zoom keys (+ / - / 0)
            elif k in (ord("+"), ord("=")):
                apply_zoom(dw // 2, dh // 2, 1.25)
                render()
            elif k == ord("-"):
                apply_zoom(dw // 2, dh // 2, 0.8)
                render()
            elif k == ord("0"):
                state["zoom"] = 1.0
                state["ox"] = state["oy"] = 0.0
                render()

            # Flechas de Pan
            elif key in ARROWS:
                dx, dy = ARROWS[key]
                step = 60 / state["zoom"]
                state["ox"] += dx * step
                state["oy"] += dy * step
                get_viewport()
                render()

            # Resetear vaca actual o vacas guardadas ('r', 'R')
            elif k in (ord("r"), ord("R")):
                if current_mask.any() or sam_pts:
                    current_mask[:] = 0
                    sam_pts.clear()
                    sam_lbs.clear()
                    undo_stack.clear()
                    state["drawing"] = 0
                    state["last_base_pos"] = None
                    print("  Máscara en edición borrada.")
                elif instances:
                    instances.pop()
                    print(f"  Vaca anterior eliminada. Quedan {len(instances)} vacas en esta foto.")
                render()

            # Ocultar / mostrar overlay ('h', 'H')
            elif k in (ord("h"), ord("H")):
                state["show_overlay"] = not state["show_overlay"]
                render()

            # Navegación
            elif k in (ord("s"), ord("S")):
                action = "skip"
                break
            elif k in (ord("b"), ord("B")):
                action = "back"
                break
            elif k in (ord("q"), ord("Q")):
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
            with open(manifest_csv, "w", newline="") as f:
                fields = ["qid", "stratum", "cow_id", "source_file", "image_file", "n_instances", "n_polygons", "status"]
                w = csv.DictWriter(f, fieldnames=fields)
                w.writeheader()
                for item in manifest.values():
                    w.writerow(item)
            print(f"  ✓ {qid} ({stratum}): {len(instances)} vaca(s) guardada(s)")
            idx += 1

    cv2.destroyAllWindows()
    print(f"\nSesión finalizada. Total anotadas: {len(manifest)}/{len(QUEUE)}")
    print(f"Manifiesto -> {manifest_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
