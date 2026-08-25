"""Hand-guided segmentation with SAM — click the cow, get a precise mask.

You click ON the target cow (left = include) and on cows-behind / background
(right = exclude). SAM produces a precise silhouette from your clicks. On accept
it (1) measures morphometry with the ArUco scale and (2) saves the binary mask —
which later doubles as a training label to fine-tune YOLO26-seg.

    python3 src/annotate_sam.py --dir data/field/raw/_grouped/6700 --cow-id 6700 --marker-size-cm 15

Per photo:
  left-click  = punto DENTRO de la vaca objetivo
  right-click = punto a EXCLUIR (vaca de atras / fondo)
  z           = deshacer ultimo punto (ctrl+z)
  ENTER/SPACE = aceptar (mide + guarda mascara)
  r           = reiniciar puntos
  s           = saltar foto
  q           = salir
Outputs: <dir>/_masks/*.png (etiquetas)  +  <dir>/sam_features.csv  +  <dir>/_annot/*.jpg
"""
from __future__ import annotations
import argparse, csv, sys
from pathlib import Path
import cv2, numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from core.aruco import ArucoDetector
from core.calibration import from_marker
from core.morphometry import measure
from ultralytics import SAM

MAX_W = 1280  # display width (photos are 4096 wide; scale down for the window)


def run_sam(sam, img, pts, labels):
    if not pts:
        return None
    r = sam(img, points=[pts], labels=[labels], verbose=False)
    if not r or r[0].masks is None or len(r[0].masks.data) == 0:
        return None
    return r[0].masks.data[0].cpu().numpy().astype(np.uint8)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--cow-id", default="")
    ap.add_argument("--marker-size-cm", type=float, default=15.0)
    ap.add_argument("--sam-model", default="mobile_sam.pt")
    a = ap.parse_args()

    d = Path(a.dir)
    (d / "_masks").mkdir(exist_ok=True)
    (d / "_annot").mkdir(exist_ok=True)
    aruco = ArucoDetector("DICT_6X6_250", allowed_ids=None, min_marker_size_px=18)
    sam = SAM(a.sam_model)

    imgs = sorted(p for p in d.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png"))
    rows = []
    print(__doc__.split("Per photo")[1])

    for p in imgs:
        full = cv2.imread(str(p))
        if full is None:
            continue
        H, W = full.shape[:2]
        scale = min(1.0, MAX_W / W)
        disp_base = cv2.resize(full, (int(W * scale), int(H * scale)))
        mks = aruco.detect(full)

        state = {"pts": [], "labels": [], "mask": None}

        def render():
            d2 = disp_base.copy()
            if state["mask"] is not None:
                m = cv2.resize(state["mask"], (d2.shape[1], d2.shape[0]), interpolation=cv2.INTER_NEAREST)
                col = np.zeros_like(d2); col[m.astype(bool)] = (0, 200, 255)
                d2 = cv2.addWeighted(d2, 1.0, col, 0.45, 0)
            for (x, y), lb in zip(state["pts"], state["labels"]):
                cv2.circle(d2, (int(x * scale), int(y * scale)), 6, (0, 255, 0) if lb == 1 else (0, 0, 255), -1)
            cv2.putText(d2, f"{p.name}  marcador:{'SI' if mks else 'NO'}", (10, 24),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            cv2.imshow("SAM", d2)

        def on_mouse(event, x, y, flags, _):
            if event == cv2.EVENT_LBUTTONDOWN:
                state["pts"].append([x / scale, y / scale]); state["labels"].append(1)
            elif event == cv2.EVENT_RBUTTONDOWN:
                state["pts"].append([x / scale, y / scale]); state["labels"].append(0)
            else:
                return
            state["mask"] = run_sam(sam, full, state["pts"], state["labels"])
            render()

        cv2.namedWindow("SAM"); cv2.setMouseCallback("SAM", on_mouse); render()
        action = None
        while True:
            k = cv2.waitKey(20) & 0xFF
            if k in (13, 10, 32): action = "accept"; break
            if k in (ord("z"), 8):  # undo last point (z or backspace)
                if state["pts"]:
                    state["pts"].pop(); state["labels"].pop()
                    state["mask"] = run_sam(sam, full, state["pts"], state["labels"]) if state["pts"] else None
                    render()
            if k == ord("r"): state["pts"].clear(); state["labels"].clear(); state["mask"] = None; render()
            if k == ord("s"): action = "skip"; break
            if k == ord("q"): action = "quit"; break
        cv2.destroyAllWindows()

        if action == "quit": break
        if action == "skip" or state["mask"] is None:
            print(f"  {p.name}: saltada"); continue

        mask = state["mask"]
        cv2.imwrite(str(d / "_masks" / f"{p.stem}.png"), (mask * 255))
        ov = full.copy(); col = np.zeros_like(ov); col[mask.astype(bool)] = (0, 200, 255)
        ov = cv2.addWeighted(ov, 1.0, col, 0.4, 0)
        cv2.imwrite(str(d / "_annot" / f"{p.stem}.jpg"), ov)

        if mks:
            m = max(mks, key=lambda dd: dd.side_length_px)
            mo = measure(mask, from_marker(m.side_length_px, a.marker_size_cm))
            row = {"photo": p.name, "cow_id": a.cow_id, "marker_px": round(m.side_length_px)}
            row.update(mo.as_features())
            rows.append(row)
            print(f"  {p.name}: largo={mo.body_length_cm}cm alto={mo.height_cm}cm area={mo.lateral_area_cm2}cm2")
        else:
            print(f"  {p.name}: mascara guardada (sin marcador -> sin medida, sirve para entrenar)")

    if rows:
        out = d / "sam_features.csv"
        with open(out, "w", newline="") as f:
            wr = csv.DictWriter(f, fieldnames=list(rows[0].keys())); wr.writeheader(); wr.writerows(rows)
        print(f"\n{len(rows)} medidas -> {out}")
    print(f"mascaras -> {d/'_masks'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
