"""Contrato de `weight_stats_campana.py`: cada estadístico se comprueba contra un valor conocido."""
import math

import numpy as np
import pytest

import eval_weight_campana as ev
import weight_stats_campana as ws


def _datos():
    rng = np.random.default_rng(3)
    area = np.linspace(9000, 17000, 20)
    y = 2.5 * area ** 0.53 * np.exp(rng.normal(0, 0.08, len(area)))
    return area, y


def test_loo_igual_al_evaluador():
    area, y = _datos()
    propio = ws.loo(area, y)
    del_evaluador = [r["pred_loo_kg"] for r in ev.evaluate(area, y, [str(i) for i in range(len(y))])["predicciones"]]
    assert propio == pytest.approx(del_evaluador, abs=1e-9)


def test_kfold_con_k_igual_n_es_loo_y_es_reproducible():
    area, y = _datos()
    assert ws.kfold_repeated(area, y, len(y), 1)[0] == pytest.approx(ws.mape(y, ws.loo(area, y)), abs=1e-12)
    assert np.array_equal(ws.kfold_repeated(area, y, 5, 20, seed=1), ws.kfold_repeated(area, y, 5, 20, seed=1))


def test_ccc_identidad_y_pearson():
    x = np.array([1.0, 2, 3, 4, 5])
    assert ws.lin_ccc(x, x) == pytest.approx(1.0)
    assert ws.lin_ccc(x, x + 1) < 1.0
    assert ws.pearson(x, 2 * x + 3) == pytest.approx(1.0)


def test_bland_altman_con_vectores_conocidos():
    ref = np.array([100.0, 200, 300, 400])
    ba = ws.bland_altman(ref, ref + np.array([2.0, -2, 2, -2]))
    assert ba["bias_kg"] == pytest.approx(0.0) and ba["n"] == 4
    sd = np.std([2, -2, 2, -2], ddof=1)
    assert ba["loa_kg"] == pytest.approx([-1.96 * sd, 1.96 * sd])


def test_exponente_fijo_recupera_a_y_predictor_medio():
    area = np.array([100, 200, 400, 800, 1600.0])
    y = 3 * area ** 0.5
    assert ws.loo_fixed_exponent(area, y, 0.5) == pytest.approx(y, abs=1e-9)
    assert ws.loo_mean(np.array([1.0, 2, 3])) == pytest.approx([2.5, 2.0, 1.5])


def test_bootstrap_sin_ruido_colapsa_a_la_ley():
    area = np.array([100, 200, 400, 800, 1600, 3200.0])
    A, B = ws.bootstrap_coef(area, 2 * area ** 0.5, B=200, seed=0)
    assert np.allclose(A, 2, atol=1e-9) and np.allclose(B, 0.5, atol=1e-9)
