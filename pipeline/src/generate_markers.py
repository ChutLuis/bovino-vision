"""Generate printable ArUco marker PDFs for collar tags.

Each page contains one marker centered, sized to the requested physical size,
with the ID printed below for visual verification.

Examples:
    python3 src/generate_markers.py --ids 0-49 --size-cm 15
    python3 src/generate_markers.py --ids 0,5,12,37 --size-cm 12 --out data/markers/test.pdf
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

import cv2
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.aruco import _DICTIONARIES  # noqa: E402  # re-uses the dictionary registry


def parse_ids(spec: str) -> list[int]:
    out: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            out.extend(range(int(a), int(b) + 1))
        elif part:
            out.append(int(part))
    return sorted(set(out))


def render_marker_png(dict_name: str, marker_id: int, pixel_size: int = 1000) -> Path:
    aruco_dict = cv2.aruco.getPredefinedDictionary(_DICTIONARIES[dict_name])
    img = cv2.aruco.generateImageMarker(aruco_dict, marker_id, pixel_size)
    tmp = Path(tempfile.gettempdir()) / f"aruco_{dict_name}_{marker_id:04d}.png"
    cv2.imwrite(str(tmp), img)
    return tmp


def build_pdf(ids: list[int], size_cm: float, dict_name: str, out_path: Path, project_label: str) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(out_path), pagesize=A4)
    page_w, page_h = A4
    marker_size_pt = size_cm * cm
    quiet_zone_pt = max(size_cm * 0.1, 1.0) * cm  # ArUco needs white border

    for marker_id in ids:
        png_path = render_marker_png(dict_name, marker_id)
        x = (page_w - marker_size_pt) / 2
        y = (page_h - marker_size_pt) / 2 + 1.5 * cm  # leave room for label below
        c.setFillColorRGB(1, 1, 1)
        c.rect(
            x - quiet_zone_pt,
            y - quiet_zone_pt,
            marker_size_pt + 2 * quiet_zone_pt,
            marker_size_pt + 2 * quiet_zone_pt,
            stroke=0,
            fill=1,
        )
        c.drawImage(
            str(png_path),
            x,
            y,
            width=marker_size_pt,
            height=marker_size_pt,
            preserveAspectRatio=True,
            mask=None,
        )
        c.setFillColorRGB(0, 0, 0)
        c.setFont("Helvetica-Bold", 24)
        label = f"ArUco {dict_name} | ID {marker_id:04d}"
        c.drawCentredString(page_w / 2, y - 1.0 * cm, label)
        c.setFont("Helvetica", 12)
        c.drawCentredString(page_w / 2, y - 1.6 * cm, f"{size_cm:.1f} cm  ·  {project_label}")
        c.showPage()

    c.save()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate printable ArUco marker PDF")
    parser.add_argument("--ids", default="0-49", help="ID spec: '0-49' or '0,1,2,5' or '0-9,20,30-35'")
    parser.add_argument("--size-cm", type=float, default=15.0, help="Physical marker side length in cm")
    parser.add_argument("--dict", default="DICT_6X6_250", help="ArUco dictionary name")
    parser.add_argument("--out", default="data/markers/markers.pdf", help="Output PDF path")
    parser.add_argument(
        "--project",
        default="Estimacion peso bovino - URL Guatemala",
        help="Label printed under each marker",
    )
    args = parser.parse_args(argv)

    if args.dict not in _DICTIONARIES:
        parser.error(f"Unknown dictionary: {args.dict}")

    ids = parse_ids(args.ids)
    if not ids:
        parser.error("No IDs parsed from --ids")

    out = Path(args.out)
    build_pdf(ids=ids, size_cm=args.size_cm, dict_name=args.dict, out_path=out, project_label=args.project)
    print(f"Wrote {len(ids)} markers to {out} (size {args.size_cm} cm, dict {args.dict})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
