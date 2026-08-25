"""Group photos into per-cow folders by capture time-gap (bursts).

Photos taken in a burst for one cow are seconds apart; moving to the next cow
leaves a bigger gap. This sorts by EXIF timestamp and splits into grupo_NNN/
folders so manual review is one-cow-at-a-time.

    python3 src/group_by_burst.py --dir data/field/raw --gap 8
    python3 src/group_by_burst.py --dir data/field/raw --gap 8 --move   # move instead of copy
"""
from __future__ import annotations
import argparse, re, shutil, sys
from datetime import datetime
from pathlib import Path
from PIL import Image


def ts(p: Path) -> datetime:
    try:
        ex = Image.open(p)._getexif() or {}
        for t in (36867, 36868, 306):  # DateTimeOriginal, Digitized, DateTime
            if t in ex and ex[t]:
                return datetime.strptime(str(ex[t]), "%Y:%m:%d %H:%M:%S")
    except Exception:
        pass
    m = re.search(r"(\d{8})[_-](\d{6})", p.name)
    if m:
        return datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S")
    return datetime.fromtimestamp(p.stat().st_mtime)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--gap", type=float, default=8.0, help="seconds gap that starts a new group")
    ap.add_argument("--move", action="store_true", help="move files instead of copying")
    a = ap.parse_args()

    d = Path(a.dir)
    imgs = [p for p in d.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png")]
    if not imgs:
        print("no images"); return 1
    items = sorted(((ts(p), p) for p in imgs), key=lambda x: x[0])

    out = d / "_grouped"; out.mkdir(exist_ok=True)
    g = 0; prev = None; gd = None; counts = []
    for t, p in items:
        if prev is None or (t - prev).total_seconds() > a.gap:
            g += 1; gd = out / f"grupo_{g:03d}"; gd.mkdir(exist_ok=True); counts.append(0)
        (shutil.move if a.move else shutil.copy)(str(p), str(gd / p.name))
        counts[-1] += 1; prev = t

    print(f"{len(items)} fotos -> {g} grupos (gap={a.gap}s)")
    multi = sum(1 for c in counts if c >= 3)
    print(f"  grupos con >=3 fotos (probable rafaga por vaca): {multi}")
    print(f"  grupos con 1-2 fotos: {sum(1 for c in counts if c < 3)}")
    print(f"\n-> {out}  (revisa carpeta por carpeta)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
