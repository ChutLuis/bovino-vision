"""Consistencia del conjunto de validación manual (data/val_clean)."""
import csv
import hashlib
import warnings
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
VAL = ROOT / "data/val_clean"


@pytest.fixture(scope="module")
def manifest():
    if not (VAL / "manifest.csv").exists():
        pytest.skip("sin data/val_clean/manifest.csv")
    return list(csv.DictReader(open(VAL / "manifest.csv")))


def test_manifest_rows_have_image_label_and_masks(manifest):
    for r in manifest:
        qid = r["qid"]
        assert next((VAL / "images").glob(f"{qid}.*"), None) is not None, f"{qid}: sin imagen"
        assert (VAL / "labels" / f"{qid}.txt").exists(), f"{qid}: sin label"
        pngs = list((VAL / "masks").glob(f"{qid}_inst*.png"))
        assert pngs, f"{qid}: sin PNG de instancia"
        assert (VAL / "masks" / f"{qid}_inst0.png").exists(), f"{qid}: falta inst0 (vaca objetivo)"


def test_manifest_counts_match_files(manifest):
    for r in manifest:
        qid = r["qid"]
        n_lines = len([l for l in (VAL / "labels" / f"{qid}.txt").read_text().splitlines() if l.strip()])
        assert n_lines == int(r["n_polygons"]), f"{qid}: n_polygons={r['n_polygons']} pero el label tiene {n_lines} líneas"
        n_png = len(list((VAL / "masks").glob(f"{qid}_inst*.png")))
        assert n_png == int(r["n_instances"]), f"{qid}: n_instances={r['n_instances']} pero hay {n_png} PNG"


def test_manifest_is_manual_and_stratified(manifest):
    assert all(r["status"] == "anotado_manual" for r in manifest)
    strata = {r["stratum"] for r in manifest}
    assert strata == {"facil", "media", "dificil"}
    assert len({r["qid"] for r in manifest}) == len(manifest)


def test_images_outside_manifest_are_reported(manifest):
    """Las imágenes fuera del manifiesto no son error, pero si son copias de las del manifiesto son ruido."""
    qids = {r["qid"] for r in manifest}
    extra = [p for p in (VAL / "images").iterdir() if p.stem not in qids]
    if not extra:
        return
    in_manifest = {hashlib.sha256(next((VAL / "images").glob(f"{q}.*")).read_bytes()).hexdigest() for q in qids}
    dups = [p.name for p in extra if hashlib.sha256(p.read_bytes()).hexdigest() in in_manifest]
    warnings.warn(f"{len(extra)} imágenes fuera del manifiesto en val_clean/images; {len(dups)} son copias exactas "
                  f"de imágenes del manifiesto (set SAM-auto de build_val_clean.py). Considera moverlas.")
