"""Hand-DRAW the cow mask with a brush + zoom — 100% manual, no model guessing.

Pintas la silueta a mano, haces zoom con la rueda para precision, y la mascara es
exactamente lo que dibujaste. El marcador (escala) se detecta solo. Al aceptar mide
la morfometria y guarda la mascara (tambien sirve de etiqueta de entrenamiento).

Estructura (por carpeta de vaca):
  mascaras/  mascara .png        listas/  overlay de finales (drives resume)
  revisar/   overlay pendiente   medidas.csv  mediciones (source=manual)

    python3 src/draw_mask.py --dir data/field/raw/_grouped/6679 --cow-id 6679 --marker-size-cm 15

Controls (por foto):
  left-drag    = PINTAR (agregar)        right-drag = BORRAR
  RUEDA raton  = zoom (hacia el cursor)  + / -      = zoom
  MEDIO-drag   = mover (pan)             flechas    = pan
  [  /  ]      = pincel mas chico / grande
  z            = deshacer ultimo trazo   h          = ocultar/mostrar overlay
  r            = limpiar todo            0          = reset zoom
  ENTER        = aceptar (mide + guarda) s = saltar     q = salir
Outputs: mascaras/*.png  +  medidas.csv  +  listas/*.jpg
"""
from __future__ import annotations
import argparse, csv, sys
from pathlib import Path
import cv2, numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from core.aruco import ArucoDetector
from core.calibration import from_marker
from core.morphometry import measure

ARROWS = {63232: (0, -1), 63233: (0, 1), 63234: (-1, 0), 63235: (1, 0),
          65362: (0, -1), 65364: (0, 1), 65361: (-1, 0), 65363: (1, 0)}

MEDIDAS_FIELDS = ["photo", "cow_id", "source", "status", "marker_px", "body_length_cm", "height_cm",
                  "chest_depth_cm", "lateral_area_cm2", "aspect_ratio", "fill_ratio"]


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def wheel_delta(flags):
    try:
        return cv2.getMouseWheelDelta(flags)
    except AttributeError:
        raw = (int(flags) >> 16) & 0xFFFF
        return raw - 65536 if raw > 32767 else raw


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--cow-id", default="")
    ap.add_argument("--marker-size-cm", type=float, default=15.0)
    ap.add_argument("--max-width", type=int, default=1280)
    ap.add_argument("--redo", action="store_true", help="re-anotar todo, ignorar lo ya hecho")
    ap.add_argument("--target", type=int, default=0, help="parar al llegar a N listas (0 = sin limite)")
    ap.add_argument("--photos", default="", help="redibujar SOLO estas fotos (nombres separados por coma)")
    a = ap.parse_args()

    d = Path(a.dir)
    for sub in ("mascaras", "listas", "revisar"):
        (d / sub).mkdir(exist_ok=True)
    aruco = ArucoDetector("DICT_6X6_250", allowed_ids=None, min_marker_size_px=18)

    imgs = sorted(p for p in d.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png"))
    csv_path = d / "medidas.csv"
    existing = {}
    if csv_path.exists():
        for r in csv.DictReader(open(csv_path)):
            existing[r["photo"]] = r
    rows = []

    def flush():  # guarda medidas.csv despues de CADA foto (a prueba de cierres)
        merged = dict(existing)
        for r in rows:
            merged[r["photo"]] = r
        if merged:
            with open(csv_path, "w", newline="") as f:
                wr = csv.DictWriter(f, fieldnames=MEDIDAS_FIELDS); wr.writeheader()
                for r in merged.values():
                    wr.writerow({k: r.get(k, "") for k in MEDIDAS_FIELDS})

    print(__doc__.split("Controls")[1])
    if a.photos:
        want = {s.strip() for s in a.photos.split(",") if s.strip()}
        todo = [p for p in imgs if p.name in want or p.stem in want]
        budget = 10 ** 9
        print(f"Redibujando {len(todo)} foto(s) marcada(s) para corregir.")
        if not todo:
            print("No se encontraron esas fotos."); return 0
    else:
        done = set() if a.redo else {q.stem for q in (d / "listas").glob("*.jpg")}
        todo = [p for p in imgs if p.stem not in done]
        if done:
            print(f"Reanudando: {len(done)} ya listas, faltan {len(todo)} de {len(imgs)}.\n")
        if not todo:
            print("Todas las fotos de esta carpeta ya estan listas. (usa --redo para rehacer)")
            return 0
        if a.target and len(done) >= a.target and not a.redo:
            print(f"Esta vaca ya tiene {len(done)} listas (>= target {a.target}). Nada que hacer.")
            return 0
        budget = (a.target - len(done)) if a.target else 10 ** 9

    for p in todo:
        full = cv2.imread(str(p))
        if full is None:
            continue
        H, W = full.shape[:2]
        mks = aruco.detect(full)
        if not mks:
            print(f"  {p.name}: sin marcador, saltada (no medible)")
            continue
        sc = min(1.0, a.max_width / W)
        disp = cv2.resize(full, (int(W * sc), int(H * sc)))
        dh, dw = disp.shape[:2]

        mask = np.zeros((dh, dw), np.uint8)
        undo = []
        s = {"Z": 1.0, "ox": 0.0, "oy": 0.0, "brush": 28, "draw": 0,
             "last": None, "cur": (0, 0), "show": True, "pan": None}

        def vis():
            vw = dw / s["Z"]; vh = dh / s["Z"]
            s["ox"] = clamp(s["ox"], 0, dw - vw); s["oy"] = clamp(s["oy"], 0, dh - vh)
            return vw, vh

        def win2base(wx, wy):
            vw, vh = vis()
            return s["ox"] + wx * vw / dw, s["oy"] + wy * vh / dh

        def render():
            vw, vh = vis()
            x0, y0 = int(s["ox"]), int(s["oy"])
            x1, y1 = min(dw, int(s["ox"] + vw)), min(dh, int(s["oy"] + vh))
            view = cv2.resize(disp[y0:y1, x0:x1], (dw, dh))
            if s["show"]:
                mc = cv2.resize(mask[y0:y1, x0:x1], (dw, dh), interpolation=cv2.INTER_NEAREST)
                col = np.zeros_like(view); col[mc.astype(bool)] = (0, 200, 255)
                view = cv2.addWeighted(view, 1.0, col, 0.45, 0)
            cv2.circle(view, s["cur"], max(1, int(s["brush"] * s["Z"])), (255, 255, 255), 1)
            cv2.putText(view, f"{p.name}  zoom:{s['Z']:.1f}x  pincel:{s['brush']}",
                        (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            cv2.imshow("DIBUJAR", view)

        def paint(wx, wy, val):
            bx, by = win2base(wx, wy)
            if s["last"] is not None:
                cv2.line(mask, s["last"], (int(bx), int(by)), val, s["brush"] * 2)
            cv2.circle(mask, (int(bx), int(by)), s["brush"], val, -1)
            s["last"] = (int(bx), int(by))

        def zoom(wx, wy, factor):
            bx, by = win2base(wx, wy)
            s["Z"] = clamp(s["Z"] * factor, 1.0, 10.0)
            vw, vh = dw / s["Z"], dh / s["Z"]
            s["ox"] = bx - wx * vw / dw; s["oy"] = by - wy * vh / dh
            vis(); render()

        def on_mouse(event, x, y, flags, _):
            s["cur"] = (x, y)
            if event == cv2.EVENT_MOUSEWHEEL:
                zoom(x, y, 1.25 if wheel_delta(flags) > 0 else 0.8); return
            if event == cv2.EVENT_MBUTTONDOWN:
                s["pan"] = (x, y); return
            if event == cv2.EVENT_MBUTTONUP:
                s["pan"] = None; return
            if event == cv2.EVENT_LBUTTONDOWN:
                s["draw"] = 1; s["last"] = None; paint(x, y, 1)
            elif event == cv2.EVENT_RBUTTONDOWN:
                s["draw"] = 2; s["last"] = None; paint(x, y, 0)
            elif event == cv2.EVENT_MOUSEMOVE:
                if s["pan"] is not None:
                    vw, vh = dw / s["Z"], dh / s["Z"]
                    s["ox"] -= (x - s["pan"][0]) * vw / dw; s["oy"] -= (y - s["pan"][1]) * vh / dh
                    s["pan"] = (x, y)
                elif s["draw"]:
                    paint(x, y, 1 if s["draw"] == 1 else 0)
            elif event in (cv2.EVENT_LBUTTONUP, cv2.EVENT_RBUTTONUP):
                if s["draw"]:
                    undo.append(mask.copy()); s["draw"] = 0; s["last"] = None
                    if len(undo) > 40: undo.pop(0)
            render()

        cv2.namedWindow("DIBUJAR"); cv2.setMouseCallback("DIBUJAR", on_mouse); render()
        action = None
        while True:
            key = cv2.waitKeyEx(20)
            if key == -1: continue
            k = key & 0xFF
            if k in (13, 10): action = "accept"; break
            elif key in ARROWS:
                dx, dy = ARROWS[key]; step = 60 / s["Z"]
                s["ox"] += dx * step; s["oy"] += dy * step; vis(); render()
            elif k in (ord("+"), ord("=")): zoom(dw // 2, dh // 2, 1.25)
            elif k == ord("-"): zoom(dw // 2, dh // 2, 0.8)
            elif k == ord("0"): s["Z"] = 1.0; s["ox"] = s["oy"] = 0.0; render()
            elif k == ord("]"): s["brush"] = min(120, s["brush"] + 4); render()
            elif k == ord("["): s["brush"] = max(3, s["brush"] - 4); render()
            elif k in (ord("z"), 8):
                if undo: undo.pop(); mask[:] = undo[-1] if undo else 0; render()
            elif k == ord("h"): s["show"] = not s["show"]; render()
            elif k == ord("r"): mask[:] = 0; undo.clear(); render()
            elif k == ord("s"): action = "skip"; break
            elif k == ord("q"): action = "quit"; break
        cv2.destroyAllWindows()

        if action == "quit": break
        if action == "skip" or mask.sum() == 0:
            print(f"  {p.name}: saltada"); continue

        full_mask = cv2.resize(mask, (W, H), interpolation=cv2.INTER_NEAREST)
        cv2.imwrite(str(d / "mascaras" / f"{p.stem}.png"), full_mask * 255)
        ov = full.copy(); col = np.zeros_like(ov); col[full_mask.astype(bool)] = (0, 200, 255)
        cv2.imwrite(str(d / "listas" / f"{p.stem}.jpg"), cv2.addWeighted(ov, 1.0, col, 0.4, 0))
        rev = d / "revisar" / f"{p.stem}.jpg"
        if rev.exists():
            rev.unlink()

        m = max(mks, key=lambda dd: dd.side_length_px)
        mo = measure(full_mask, from_marker(m.side_length_px, a.marker_size_cm))
        row = {"photo": p.name, "cow_id": a.cow_id, "source": "manual", "status": "manual",
               "marker_px": round(m.side_length_px)}
        row.update(mo.as_features())
        rows.append(row)
        flush()  # persistir de inmediato
        print(f"  {p.name}: largo={mo.body_length_cm}cm alto={mo.height_cm}cm area={mo.lateral_area_cm2}cm2 (guardado)")
        if len(rows) >= budget:
            print(f"\nLlegaste al target ({a.target}) para {a.cow_id}.")
            break

    flush()
    print(f"\n{len(rows)} nuevas guardadas -> {csv_path}")
    print(f"mascaras -> {d/'mascaras'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
