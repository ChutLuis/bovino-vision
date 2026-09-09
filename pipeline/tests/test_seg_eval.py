"""Pruebas de las funciones puras de evaluación de segmentación (core/seg_eval.py)."""
from pathlib import Path

import numpy as np
import pytest

from core.seg_eval import (bootstrap_paired_by_group, evaluate_image, greedy_match, iou,
                           load_gt_polygons, parse_label_lines, rasterize)

ROOT = Path(__file__).resolve().parent.parent


def square(h, w, y0, x0, size):
    m = np.zeros((h, w), np.uint8)
    m[y0:y0 + size, x0:x0 + size] = 1
    return m


def label_text(n_polys):
    # cuadrados normalizados distintos, una línea por instancia
    lines = []
    for k in range(n_polys):
        x0, y0 = 0.05 + 0.18 * k, 0.1
        lines.append(f"0 {x0} {y0} {x0 + 0.1} {y0} {x0 + 0.1} {y0 + 0.2} {x0} {y0 + 0.2}")
    return "\n".join(lines) + "\n"


@pytest.mark.parametrize("n", [1, 2, 5])
def test_parse_label_lines_one_instance_per_line(n):
    polys = parse_label_lines(label_text(n))
    assert len(polys) == n
    for p in polys:
        assert p.shape == (4, 2)
        # el id de clase nunca entra como coordenada
        assert (p[:, 0] > 0).all() and (p[:, 1] > 0).all()


def test_old_whole_file_parse_fails_on_two_instances():
    """Documenta el bug histórico: leer el archivo entero con split() mezcla ids y coordenadas."""
    toks = label_text(2).split()
    with pytest.raises(ValueError):
        np.array(toks[1:], dtype=float).reshape(-1, 2)  # 17 tokens -> impar


def test_real_multi_instance_label_if_present():
    lbl = ROOT / "data/val_clean/labels/12_06_chaparrita.txt"
    if not lbl.exists():
        pytest.skip("sin data/val_clean")
    masks = load_gt_polygons(lbl, 640, 480)
    assert len(masks) == 2 and all(m.sum() > 0 for m in masks)


def test_rasterize_area_roughly_right():
    poly = np.array([[0.25, 0.25], [0.75, 0.25], [0.75, 0.75], [0.25, 0.75]])
    m = rasterize(poly, 100, 100)
    assert 2400 <= m.sum() <= 2700


def test_greedy_match_swapped_order():
    a = square(100, 100, 10, 10, 30)
    b = square(100, 100, 60, 60, 30)
    M, matched = greedy_match([b, a], [a, b])
    assert M.shape == (2, 2)
    assert matched == [1.0, 1.0]


def test_greedy_match_unmatched_gt_is_zero_and_extra_pred_is_fp():
    a = square(100, 100, 10, 10, 30)
    b = square(100, 100, 60, 60, 30)
    extra = square(100, 100, 5, 60, 20)
    ev = evaluate_image([a, extra], [a, b], target=0)
    assert ev.eligio_objetivo is True
    assert ev.recall_inst_050 == 0.5
    assert ev.fp == 1
    assert ev.iou_objetivo == 1.0
    assert ev.err_area_objetivo == 0.0


def test_evaluate_image_largest_pred_not_target():
    target = square(200, 200, 10, 10, 40)      # vaca objetivo, chica
    other = square(200, 200, 100, 100, 80)     # vaca de adelante, grande
    ev = evaluate_image([target, other], [target, other], target=0)
    assert ev.eligio_objetivo is False         # la regla "mayor área" elige la otra
    assert ev.recall_inst_050 == 1.0           # pero ambas se segmentaron


def test_evaluate_image_no_detection():
    gt = square(50, 50, 5, 5, 20)
    ev = evaluate_image([], [gt])
    assert ev.sin_deteccion and not ev.eligio_objetivo and ev.iou_objetivo == 0.0 and ev.err_area_objetivo == -1.0


def test_iou_symmetry_and_bounds():
    a = square(50, 50, 0, 0, 20)
    b = square(50, 50, 10, 10, 20)
    assert 0 < iou(a, b) < 1 and iou(a, b) == iou(b, a) and iou(a, a) == 1.0


def test_bootstrap_by_group_constant_delta_collapses():
    a = {f"vaca{i}": [0.8, 0.82] for i in range(6)}
    b = {k: [v + 0.1 for v in vals] for k, vals in a.items()}
    r = bootstrap_paired_by_group(a, b, n_boot=500, seed=1)
    assert r["n_grupos"] == 6
    assert abs(r["dif_media"] - 0.1) < 1e-6
    assert abs(r["ic95"][0] - 0.1) < 1e-6 and abs(r["ic95"][1] - 0.1) < 1e-6


def test_bootstrap_by_group_resamples_groups_not_images():
    # un grupo con muchas imágenes no debe pesar más que uno con una
    a = {"A": [0.5] * 20, "B": [0.5]}
    b = {"A": [0.5] * 20, "B": [0.9]}
    r = bootstrap_paired_by_group(a, b, n_boot=200, seed=0)
    assert abs(r["dif_media"] - 0.2) < 1e-6  # media de (0, 0.4) por grupo
