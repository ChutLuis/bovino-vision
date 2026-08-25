"""Auto-triage field photos: usable / review / reject for the weight dataset.

Scores each photo on: marker decoded & big enough, exactly one clearly-dominant
cow, cow fully inside frame (not cut off), cow big enough (not too far).
Writes a CSV + copies an overlay into keep/ review/ reject/ subfolders.

    python3 src/triage_photos.py --dir data/field/raw

NOTE: "keep" = photo is geometrically usable. It still needs a LOGGED WEIGHT
for that cow to be usable for the regression — that link comes from your logbook.
"""
from __future__ import annotations
import argparse, csv, sys
from pathlib import Path
import cv2, numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from core.aruco import ArucoDetector
from core.segmenter import CowSegmenter


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--conf", type=float, default=0.45)
    ap.add_argument("--min-marker-px", type=float, default=45)
    ap.add_argument("--min-cow-img-frac", type=float, default=0.04)
    args = ap.parse_args()

    d = Path(args.dir)
    for sub in ("keep", "review", "reject"):
        (d / "_triage" / sub).mkdir(parents=True, exist_ok=True)

    aruco = ArucoDetector("DICT_6X6_250", allowed_ids=None, min_marker_size_px=18)
    seg = CowSegmenter("models/yolo26n-seg.pt", cow_class_id=19, min_confidence=args.conf)

    imgs = sorted(p for p in d.iterdir()
                  if p.suffix.lower() in (".jpg", ".jpeg", ".png") and not p.name.startswith("."))
    rows, counts = [], {"keep": 0, "review": 0, "reject": 0}

    for p in imgs:
        fr = cv2.imread(str(p))
        if fr is None:
            continue
        H, W = fr.shape[:2]
        mks = aruco.detect(fr)
        marker_px = max((m.side_length_px for m in mks), default=0.0)
        marker_ok = marker_px >= args.min_marker_px
        cows = seg.segment(fr)
        n = len(cows)

        verdict, why = "keep", []
        dom_frac = img_frac = 0.0
        edge = False
        if not marker_ok:
            verdict, why = "reject", ["sin marcador decodable"]
        elif n == 0:
            verdict, why = "reject", ["sin vaca"]
        else:
            dom = max(cows, key=lambda c: c.area_px)
            tot = sum(c.area_px for c in cows)
            dom_frac = dom.area_px / tot if tot else 0
            img_frac = dom.area_px / (H * W)
            x1, y1, x2, y2 = dom.bbox_xyxy
            mx, my = 0.015 * W, 0.015 * H
            edge = x1 <= mx or y1 <= my or x2 >= W - mx or y2 >= H - my
            if edge:
                verdict = "review"; why.append("vaca tocando borde (posible corte)")
            if n >= 3 and dom_frac < 0.5:
                verdict = "review"; why.append("muchas vacas encimadas (ambiguo)")
            if img_frac < args.min_cow_img_frac:
                verdict = "review"; why.append("vaca muy pequena/lejos")

        counts[verdict] += 1
        rows.append({"photo": p.name, "verdict": verdict, "marker_px": round(marker_px),
                     "n_cows": n, "dominant_frac": round(dom_frac, 2),
                     "cow_img_frac": round(img_frac, 3), "reason": "; ".join(why) or "ok"})

        # overlay — only for keep/review (skip rejects to save time/disk on big batches)
        if verdict != "reject":
            ann = fr.copy()
            if n:
                dom = max(cows, key=lambda c: c.area_px)
                colored = np.zeros_like(ann); colored[dom.mask.astype(bool)] = (0, 200, 255)
                ann = cv2.addWeighted(ann, 1.0, colored, 0.4, 0)
                x1, y1, x2, y2 = dom.bbox_xyxy
                cv2.rectangle(ann, (x1, y1), (x2, y2), (0, 200, 255), 3)
            ann = ArucoDetector.draw(ann, mks)
            cv2.putText(ann, verdict.upper(), (30, 70), cv2.FONT_HERSHEY_SIMPLEX, 2.0,
                        (0, 255, 0) if verdict == "keep" else (0, 165, 255), 4)
            cv2.imwrite(str(d / "_triage" / verdict / f"{p.stem}.jpg"), ann)

    with open(d / "_triage" / "triage.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)

    print(f"Procesadas {len(rows)} fotos:")
    print(f"  KEEP   (usables):  {counts['keep']}")
    print(f"  REVIEW (revisar):  {counts['review']}")
    print(f"  REJECT (descartar):{counts['reject']}")
    print(f"\nCSV + overlays -> {d/'_triage'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
