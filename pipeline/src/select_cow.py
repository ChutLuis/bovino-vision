"""Manual cow isolation — draw a box around the TARGET cow so the segmenter
ignores the ones behind / beside her.

For each photo: the marker is detected on the FULL image (scale), then you drag a
rectangle around the target cow; segmentation runs only inside that box, so a cow
behind can't contaminate the mask. Measurements are written to a CSV.

    python3 src/select_cow.py --dir data/field/raw/_grouped/grupo_007 --marker-size-cm 15

Controls (per photo): drag a box around the cow -> ENTER to confirm.
  - draw nothing + ENTER  = skip this photo
  - ESC                   = quit
"""
from __future__ import annotations
import argparse, csv, sys
from pathlib import Path
import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent))
from core.aruco import ArucoDetector
from core.calibration import from_marker
from core.segmenter import CowSegmenter
from core.morphometry import measure


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--marker-size-cm", type=float, default=15.0)
    ap.add_argument("--out", default="")
    ap.add_argument("--cow-id", default="", help="optional: label all photos in this folder with one cow id")
    a = ap.parse_args()

    d = Path(a.dir)
    out = Path(a.out) if a.out else d / "manual_features.csv"
    aruco = ArucoDetector("DICT_6X6_250", allowed_ids=None, min_marker_size_px=18)
    seg = CowSegmenter("models/yolo26n-seg.pt", cow_class_id=19, min_confidence=0.40)

    imgs = sorted(p for p in d.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png"))
    rows = []
    print("Arrastra un recuadro alrededor de la VACA objetivo. ENTER=ok | nada+ENTER=saltar | ESC=salir")
    for p in imgs:
        fr = cv2.imread(str(p))
        if fr is None:
            continue
        mks = aruco.detect(fr)
        disp = ArucoDetector.draw(fr.copy(), mks)
        win = f"{p.name} | marcador: {'SI' if mks else 'NO'}"
        roi = cv2.selectROI(win, disp, showCrosshair=True, fromCenter=False)
        cv2.destroyAllWindows()
        x, y, w, h = (int(v) for v in roi)
        if w == 0 or h == 0:
            print(f"  {p.name}: saltada"); continue
        if not mks:
            print(f"  {p.name}: SIN marcador -> no medible, saltada"); continue

        m = max(mks, key=lambda dd: dd.side_length_px)
        calib = from_marker(m.side_length_px, a.marker_size_cm)
        crop = fr[y:y + h, x:x + w]
        cow = CowSegmenter.largest(seg.segment(crop))
        if cow is None:
            print(f"  {p.name}: sin vaca en el recuadro, saltada"); continue
        mo = measure(cow.mask, calib)
        row = {"photo": p.name, "cow_id": a.cow_id, "marker_px": round(m.side_length_px)}
        row.update(mo.as_features())
        rows.append(row)
        print(f"  {p.name}: largo={mo.body_length_cm}cm alto={mo.height_cm}cm area={mo.lateral_area_cm2}cm2")

    if rows:
        with open(out, "w", newline="") as f:
            wr = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            wr.writeheader(); wr.writerows(rows)
        print(f"\n{len(rows)} medidas -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
