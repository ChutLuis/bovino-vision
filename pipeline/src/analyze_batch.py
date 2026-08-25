"""Quick diagnostic: run ArUco + cow segmentation over a folder, save overlays.

    python3 src/analyze_batch.py --dir data/test
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path
import cv2, numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from core.aruco import ArucoDetector
from core.segmenter import CowSegmenter

COLORS = [(0,200,255),(255,128,0),(0,255,128),(255,0,200),(128,128,255),(0,128,255)]

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="data/test")
    ap.add_argument("--conf", type=float, default=0.40)
    args = ap.parse_args()
    d = Path(args.dir)
    out = d / "_overlays"; out.mkdir(exist_ok=True)

    aruco = ArucoDetector("DICT_6X6_250", allowed_ids=None, min_marker_size_px=18)
    seg = CowSegmenter(model_path="models/yolo26n-seg.pt", cow_class_id=19, min_confidence=args.conf)

    imgs = sorted([p for p in d.iterdir() if p.suffix.lower() in (".jpg",".jpeg",".png") and "_check" not in p.stem])
    print(f"{'file':42} {'res':>11} {'mk':>3} {'marker_ids':>14} {'cows':>4}  cow_confs")
    for p in imgs:
        fr = cv2.imread(str(p))
        if fr is None:
            print(f"{p.name:42} UNREADABLE"); continue
        H,W = fr.shape[:2]
        mks = aruco.detect(fr)
        cows = seg.segment(fr)
        ids = ",".join(str(m.marker_id) for m in mks) if mks else "-"
        confs = " ".join(f"{c.confidence:.2f}" for c in sorted(cows,key=lambda c:-c.confidence))
        print(f"{p.name[:42]:42} {W}x{H:<6} {len(mks):>3} {ids:>14} {len(cows):>4}  {confs}")
        ann = fr.copy()
        for i,c in enumerate(sorted(cows,key=lambda c:-c.area_px)):
            col = COLORS[i%len(COLORS)]
            colored = np.zeros_like(ann); colored[c.mask.astype(bool)] = col
            ann = cv2.addWeighted(ann,1.0,colored,0.4,0)
            x1,y1,x2,y2 = c.bbox_xyxy
            cv2.rectangle(ann,(x1,y1),(x2,y2),col,3)
            cv2.putText(ann,f"#{i+1} {c.confidence:.2f}",(x1,max(0,y1-8)),cv2.FONT_HERSHEY_SIMPLEX,1.2,col,3)
        ann = ArucoDetector.draw(ann, mks)
        cv2.imwrite(str(out / f"{p.stem}_ov.jpg"), ann)
    print(f"\noverlays -> {out}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
