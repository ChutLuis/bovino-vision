"""Geometría del emulador de la ruta del APK (core/segmenter_litert.py) contra las fórmulas de image.ts/segment.ts."""
import numpy as np
import pytest

from core.segmenter_litert import (INPUT_SIZE, MASK_SIZE, PAD_VALUE, Letterbox, box_in_original, js_round,
                                   letterbox_nchw, mask_from_row, prototype_index_maps)


def test_js_round_half_up():
    assert js_round(2.5) == 3 and js_round(2.49) == 2 and js_round(0.5) == 1


@pytest.mark.parametrize("w,h,scale,cw,ch,px,py", [
    (1280, 960, 0.5, 640, 480, 0, 80),           # fotos del benchmark
    (4000, 2250, 0.16, 640, 360, 0, 140),        # ráfagas
    (640, 640, 1.0, 640, 640, 0, 0),
    (900, 1200, 640 / 1200, 480, 640, 80, 0),    # vertical
])
def test_letterbox_geometry_matches_image_ts(w, h, scale, cw, ch, px, py):
    img = np.zeros((h, w, 3), np.uint8)
    inp, lb = letterbox_nchw(img)
    assert inp.shape == (3, INPUT_SIZE, INPUT_SIZE) and inp.dtype == np.float32
    assert abs(lb.scale - scale) < 1e-12
    assert (lb.content_width, lb.content_height, lb.pad_x, lb.pad_y) == (cw, ch, px, py)


def test_letterbox_values_and_padding():
    img = np.full((960, 1280, 3), 200, np.uint8)
    img[..., 0] = 50  # canal R distinto para comprobar el orden de planos
    inp, lb = letterbox_nchw(img)
    content = inp[:, lb.pad_y:lb.pad_y + lb.content_height, :]
    assert np.allclose(content[0], 50 / 255, atol=1e-6) and np.allclose(content[1], 200 / 255, atol=1e-6)
    assert np.allclose(inp[:, :lb.pad_y, :], PAD_VALUE) and np.allclose(inp[:, lb.pad_y + lb.content_height:, :], PAD_VALUE)


def test_prototype_index_maps_monotonic_and_bounded():
    lb = Letterbox(1280, 960, 0.5, 640, 480, 0, 80)
    px, py = prototype_index_maps(lb)
    assert px.shape == (1280,) and py.shape == (960,)
    assert px.min() == 0 and px.max() == MASK_SIZE - 1
    assert py.min() == 80 * MASK_SIZE // INPUT_SIZE and py.max() == (80 + 479) * MASK_SIZE // INPUT_SIZE
    assert (np.diff(px) >= 0).all() and (np.diff(py) >= 0).all()


def test_mask_from_row_counts_pixels_like_segment_ts():
    lb = Letterbox(1280, 960, 0.5, 640, 480, 0, 80)
    protos = np.zeros((32, MASK_SIZE, MASK_SIZE), np.float32)
    protos[0, :, :80] = 1.0          # prototipo 0 positivo en la mitad izquierda de la rejilla
    row = np.zeros(38, np.float32)
    row[:4] = [0, 0, INPUT_SIZE, INPUT_SIZE]  # caja = toda la imagen
    row[6] = 1.0                      # coeficiente solo del prototipo 0
    m = mask_from_row(row, protos, lb)
    px, py = prototype_index_maps(lb)
    esperado = int((px < 80).sum()) * 960
    assert m.shape == (960, 1280) and int(m.sum()) == esperado
    # con caja restringida a la mitad derecha, la máscara queda vacía
    row[:4] = [INPUT_SIZE / 2, 0, INPUT_SIZE, INPUT_SIZE]
    assert mask_from_row(row, protos, lb).sum() == 0


def test_box_in_original_undoes_letterbox_and_clamps():
    lb = Letterbox(1280, 960, 0.5, 640, 480, 0, 80)
    row = np.array([32.0, 100.0, 640.0, 700.0], np.float32)
    assert box_in_original(row, lb) == (64.0, 40.0, 1280.0, 960.0)
