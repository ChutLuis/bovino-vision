"""Contrato de `eval_weight_campana.py`.

(1) Sobre el piloto (`features_fotos_hoy.csv`, 34 vacas con una foto) el ajuste log-log reproduce los
coeficientes del bundle vigente (a = 0.375, b = 0.706) y el MAPE LOO de 7.71 %.
(2) Con una bitácora sin pesos el programa avisa por stderr, no escribe nada y devuelve 2.
(3) Con una campaña sintética (40 vacas × 5 fotos seleccionadas más fotos a 2.5 y 3.5 m, esquema del
CSV de medidas, peso = 0.4·área^0.7·ruido lognormal σ = 0.05) recupera a y b, escribe `metricas.json`
con todas las claves del contrato y evalúa los pliegues a 2.5 y 3.5 m.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import eval_weight_campana as ev

ROOT = Path(__file__).resolve().parent.parent
PILOTO = ROOT / "data/field/features_fotos_hoy.csv"

COLUMNAS_FEATURES = [
    "foto", "fila", "nombre", "arete", "telefono", "marker_px", "px_per_cm", "distancia_m", "nivel_distancia",
    "cow_conf", "area_px", "lateral_area_cm2", "lateral_area_cm2_corr", "body_length_cm", "height_cm",
    "chest_depth_cm", "aspect_ratio", "fill_ratio", "marcador_en_caja", "seleccionada_3m", "estado",
]
COLUMNAS_BITACORA = ["fila", "nombre", "arete", "categoria", "peso_lb1", "peso_lb2", "peso_kg", "telefono", "notas"]
CLAVES_CONTRATO = {
    "a", "b", "mape", "mape_ic95", "r2", "rmse", "mae", "sigma_log", "t", "n", "factor_ip",
    "aic_alometrico", "aic_multivariado", "mape_pliegue_distancia",
    "area", "mape_multivariado", "icc_repetibilidad", "cv_intra_pct", "bland_altman", "alternativa",
    "n_fotos", "seleccion",
}


def test_piloto_reproduce_coeficientes_y_mape_loo():
    df = pd.read_csv(PILOTO).dropna(subset=["lateral_area_cm2", "weight_kg"])
    assert len(df) == 34
    area = df["lateral_area_cm2"].to_numpy(float)
    peso = df["weight_kg"].to_numpy(float)
    a, b = ev.ajustar_loglog(area, peso)
    assert a == pytest.approx(0.375, abs=0.005)
    assert b == pytest.approx(0.706, abs=0.005)
    assert ev.mape(peso, ev.loo_loglog(area, peso)) == pytest.approx(7.71, abs=0.05)


def _fila_foto(fila, nombre, i, area, d, nivel, sel, estado="ok"):
    corr = area * ((d + 0.5) / d) ** 2
    return {
        "foto": f"IMG_{fila:02d}_{i:02d}.jpg", "fila": fila, "nombre": nombre, "arete": f"{fila:06d}",
        "telefono": "xiaomi_15_ultra", "marker_px": round(2616.9 * 0.15 / d, 2), "px_per_cm": round(2616.9 * 0.01 / d, 4),
        "distancia_m": round(d, 3), "nivel_distancia": nivel, "cow_conf": 0.95, "area_px": round(area * 70),
        "lateral_area_cm2": round(area, 2), "lateral_area_cm2_corr": round(corr, 2),
        "body_length_cm": round(0.012 * area + 40, 2), "height_cm": round(0.006 * area + 50, 2),
        "chest_depth_cm": 80.0, "aspect_ratio": 1.7, "fill_ratio": 0.5, "marcador_en_caja": 1,
        "seleccionada_3m": sel, "estado": estado,
    }


def _campana_sintetica(tmp_path: Path, con_pesos: bool, n_vacas=40, seed=7):
    """CSV de medidas y bitácora con el esquema de la campaña; peso = 0.4·área^0.7·ruido lognormal σ = 0.05."""
    rng = np.random.default_rng(seed)
    filas, bitacora = [], []
    for fila in range(1, n_vacas + 1):
        nombre = f"Vaca{fila:02d}"
        area_real = rng.uniform(11000, 20000)
        i = 0
        for _ in range(5):  # seleccionadas, alrededor de 3.0 m
            i += 1
            filas.append(_fila_foto(fila, nombre, i, area_real * rng.lognormal(0, 0.03), rng.uniform(2.85, 3.15), 3.0, 1))
        for nivel in (2.5, 3.5):  # pliegues de distancia
            for _ in range(3):
                i += 1
                filas.append(_fila_foto(fila, nombre, i, area_real * rng.lognormal(0, 0.03), rng.uniform(nivel - 0.1, nivel + 0.1), nivel, 0))
        i += 1
        filas.append(_fila_foto(fila, nombre, i, area_real, 3.0, 3.0, 0, estado="sin_marcador"))
        peso = 0.4 * area_real ** 0.7 * rng.lognormal(0, 0.05)
        bitacora.append({"fila": fila, "nombre": nombre, "arete": f"{fila:06d}", "categoria": "", "peso_lb1": "",
                         "peso_lb2": "", "peso_kg": f"{peso:.1f}" if con_pesos else "",
                         "telefono": "xiaomi_15_ultra", "notas": ""})
    f = pd.DataFrame(filas)[COLUMNAS_FEATURES]
    b = pd.DataFrame(bitacora)[COLUMNAS_BITACORA]
    f.to_csv(tmp_path / "features.csv", index=False)
    b.to_csv(tmp_path / "bitacora.csv", index=False)
    return tmp_path / "features.csv", tmp_path / "bitacora.csv"


def test_bitacora_sin_pesos_devuelve_2_y_no_escribe(tmp_path, capsys):
    features, bitacora = _campana_sintetica(tmp_path, con_pesos=False)
    out = tmp_path / "salida"
    rc = ev.main(["--features", str(features), "--bitacora", str(bitacora), "--out", str(out), "--n-boot", "50"])
    assert rc == 2
    assert "sin pesos en la bitácora: peso_kg, peso_lb1 y peso_lb2 vacíos en las 40 filas" in capsys.readouterr().err
    assert not out.exists() or not any(out.iterdir())


def test_campana_sintetica_recupera_modelo_y_escribe_metricas(tmp_path):
    features, bitacora = _campana_sintetica(tmp_path, con_pesos=True)
    out = tmp_path / "salida"
    rc = ev.main(["--features", str(features), "--bitacora", str(bitacora), "--out", str(out), "--n-boot", "200"])
    assert rc == 0
    for nombre in ("resultados_loo.csv", "metricas.json", "pred_vs_real.png"):
        assert (out / nombre).is_file(), nombre

    m = json.loads((out / "metricas.json").read_text(encoding="utf-8"))
    assert CLAVES_CONTRATO <= set(m)
    assert m["n"] == 40 and m["n_fotos"] == 200 and m["seleccion"] == "seleccionada_3m"

    # el peso se generó con el área cruda: ese modelo (principal o alternativa) recupera a = 0.4 y b = 0.7
    crudo = m if m["area"] == "lateral_area_cm2" else m["alternativa"]
    assert crudo["area"] == "lateral_area_cm2"
    assert crudo["a"] == pytest.approx(0.4, rel=0.10)
    assert crudo["b"] == pytest.approx(0.7, rel=0.10)
    assert m["mape_ic95"][0] <= m["mape"] <= m["mape_ic95"][1]
    assert m["factor_ip"] == pytest.approx(np.exp(m["t"] * m["sigma_log"] * np.sqrt(1 + 1 / m["n"])), rel=1e-3)

    pliegue = m["mape_pliegue_distancia"]
    assert {"2.5", "3.5", "n_2.5", "n_3.5"} <= set(pliegue)
    assert pliegue["n_2.5"] == 40 and pliegue["n_3.5"] == 40
    assert pliegue["2.5"] is not None and pliegue["3.5"] is not None
    assert 0 < m["icc_repetibilidad"] <= 1
    assert m["bland_altman"] is None

    loo = pd.read_csv(out / "resultados_loo.csv")
    assert list(loo.columns) == ["fila", "nombre", "peso_kg", "pred_kg", "ape_pct", "modelo"]
    assert len(loo) == 40
    assert set(loo["modelo"]) == {f"alometrico_{m['area']}"}
