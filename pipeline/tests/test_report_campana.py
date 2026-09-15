"""Contrato de report_campana.py sobre un CSV sintético: pendiente cruda conocida, Δ*, ICC(1) y archivos generados."""
import math

import numpy as np
import pandas as pd
import pytest
from PIL import Image

import report_campana as rc

F_PX = 2616.9
SESGO_POR_M = 0.08  # el área crece 8 %/m con la distancia dentro de cada animal
SALIDAS = ["resumen.md", "repetibilidad.csv", "repetibilidad.png", "robustez_distancia.csv",
           "robustez_distancia_delta.csv", "robustez_distancia.png", "robustez_distancia.md"]


def sintetico(n_vacas=6, por_nivel=3, sesgo=SESGO_POR_M, ruido=0.01, seed=0) -> pd.DataFrame:
    """6 vacas × 9 fotos en tres niveles (2.5, 3.0, 3.5 m) con el esquema de features_campana_20260912.csv."""
    rng = np.random.default_rng(seed)
    filas = []
    for fila in range(1, n_vacas + 1):
        base = 12000.0 + 900.0 * fila
        fotos = []
        for nivel in rc.NIVELES:
            for _ in range(por_nivel):
                d = nivel + rng.uniform(-0.15, 0.15)
                area = base * math.exp(sesgo * (d - 3.0)) * math.exp(rng.normal(0.0, ruido))
                fotos.append((d, area))
        orden = sorted(range(len(fotos)), key=lambda i: (abs(fotos[i][0] - 3.0), i))
        seleccion = set(orden[:rc.N_SELECCION])
        for i, (d, area) in enumerate(fotos):
            marker_px = F_PX * 0.15 / d
            filas.append({"foto": f"IMG_{fila:02d}_{i:02d}.jpg", "fila": fila, "nombre": f"Vaca{fila}", "arete": "",
                          "telefono": "xiaomi_15_ultra", "marker_px": round(marker_px, 2),
                          "px_per_cm": round(marker_px / 15.0, 4), "distancia_m": round(d, 3),
                          "nivel_distancia": min(rc.NIVELES, key=lambda n: abs(n - d)), "cow_conf": 0.9,
                          "area_px": round(area * (marker_px / 15.0) ** 2), "lateral_area_cm2": round(area, 2),
                          "lateral_area_cm2_corr": round(area * ((d + 0.5) / d) ** 2, 2),
                          "body_length_cm": 150.0, "height_cm": 125.0, "chest_depth_cm": 70.0, "aspect_ratio": 1.6,
                          "fill_ratio": 0.5, "marcador_en_caja": 1, "seleccionada_3m": int(i in seleccion),
                          "estado": "ok"})
    return pd.DataFrame(filas)


def escribir_entradas(tmp_path, feat: pd.DataFrame):
    feat.to_csv(tmp_path / "features.csv", index=False)
    filas = sorted(feat["fila"].unique())
    pd.DataFrame({"fila": filas, "nombre": [f"Vaca{f}" for f in filas], "arete": "", "categoria": "", "peso_lb1": "",
                  "peso_lb2": "", "peso_kg": "", "telefono": "xiaomi_15_ultra", "notas": ""}).to_csv(
        tmp_path / "bitacora.csv", index=False)
    feat.assign(grupo="g")[["foto", "grupo", "fila", "nombre", "arete", "telefono"]].to_csv(
        tmp_path / "fotos_por_vaca.csv", index=False)
    return ["--features", str(tmp_path / "features.csv"), "--bitacora", str(tmp_path / "bitacora.csv"),
            "--fotos-por-vaca", str(tmp_path / "fotos_por_vaca.csv")]


def test_pendiente_cruda_y_delta_cruce():
    ok = sintetico().assign(area_corr=lambda d: rc.area_corregida(d["lateral_area_cm2"], d["distancia_m"], 0.5))
    curva = rc.curva_delta(ok, rc.DELTAS)
    assert list(curva["delta_m"]) == list(rc.DELTAS)
    cruda = curva.iloc[0]["pendiente_pct_por_m"]
    assert abs(cruda - 100 * SESGO_POR_M) < 1.5, cruda
    delta_star = rc.delta_cruce_cero(curva)
    assert np.isfinite(delta_star) and delta_star > 0
    # la corrección con Δ* deja la pendiente residual cerca de cero
    residual = rc.curva_delta(ok, (delta_star,)).iloc[0]["pendiente_pct_por_m"]
    assert abs(residual) < 0.5, residual


def test_icc1_varianza_intra_nula_y_desbalance():
    grupos = [1, 1, 1, 2, 2, 2, 3, 3, 3]
    assert rc.icc1(grupos, [5, 5, 5, 7, 7, 7, 9, 9, 9]) == pytest.approx(1.0)
    assert rc.icc1([1, 1, 2, 2, 2, 3, 3, 3, 3], [5, 5, 7, 7, 7, 9, 9, 9, 9]) == pytest.approx(1.0)
    rng = np.random.default_rng(1)
    assert rc.icc1(rng.integers(0, 5, 200), rng.normal(size=200)) < 0.3
    assert math.isnan(rc.icc1([1, 1, 1], [1, 2, 3]))


def test_genera_archivos_sin_mosaico(tmp_path):
    out = tmp_path / "informe"
    assert rc.main(escribir_entradas(tmp_path, sintetico()) + ["--out", str(out)]) == 0
    for nombre in SALIDAS:
        assert (out / nombre).stat().st_size > 0, nombre
    assert not (out / "mosaico_seleccion_3m.jpg").exists()
    assert list(pd.read_csv(out / "repetibilidad.csv").columns) == [
        "fila", "nombre", "n_ok", "n_sel", "mediana_area", "mediana_area_corr", "cv_area_pct", "cv_area_corr_pct",
        "cv_area_sel_pct", "cv_area_corr_sel_pct"]
    rob = pd.read_csv(out / "robustez_distancia.csv")
    assert list(rob.columns) == ["nivel", "n_fotos", "n_vacas", "cociente_area", "cociente_area_corr"]
    assert rob["n_fotos"].sum() == 54 and (rob["n_vacas"] == 6).all()
    delta = pd.read_csv(out / "robustez_distancia_delta.csv")
    assert list(delta.columns) == ["delta_m", "pendiente_pct_por_m", "cv_intra_mediana_pct"]
    assert len(delta) == 11 and delta["pendiente_pct_por_m"].is_monotonic_decreasing
    resumen = (out / "resumen.md").read_text()
    assert "## Repetibilidad" in resumen and "## Decisión → evidencia" in resumen
    assert "6/6" in resumen  # los seis animales tienen 5 seleccionadas
    assert "mosaico" not in resumen


def test_mosaico_con_fotos(tmp_path):
    feat = sintetico()
    fotos = tmp_path / "fotos"
    fotos.mkdir()
    for foto in feat["foto"]:
        Image.new("RGB", (64, 48), (120, 90, 60)).save(fotos / foto, "JPEG")
    out = tmp_path / "informe"
    assert rc.main(escribir_entradas(tmp_path, feat) + ["--out", str(out), "--fotos", str(fotos)]) == 0
    mosaico = out / "mosaico_seleccion_3m.jpg"
    assert 0 < mosaico.stat().st_size <= rc.MOSAICO_MAX_BYTES
    with Image.open(mosaico) as im:
        assert im.size[0] == 6 * 320 and im.size[1] > 240  # 6 animales → 6 columnas, 1 fila con etiqueta
    assert "mosaico_seleccion_3m.jpg" in (out / "resumen.md").read_text()
