"""Contrato de make_weight_bundle.py: el weight_model.json que consume la app, generado desde metricas.json."""
import json
import math
import subprocess
import sys
from pathlib import Path

import pytest

import make_weight_bundle as mwb

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "src" / "make_weight_bundle.py"
BUNDLE_APP = ROOT.parent / "app" / "assets" / "model_bundle" / "weight_model.json"
CLAVES = ["a", "b", "interval", "version", "fuente"]
CLAVES_INTERVAL = ["sigma_log", "t", "n", "factor"]

T, SIGMA, N = 2.024, 0.08, 40
METRICAS = {
    "a": 0.41, "b": 0.69,
    "mape": 6.5, "mape_ic95": [5.1, 8.0], "r2": 0.91, "rmse": 21.3, "mae": 16.8,
    "sigma_log": SIGMA, "t": T, "n": N, "factor_ip": math.exp(T * SIGMA * math.sqrt(1 + 1 / N)),
    "aic_alometrico": -120.5, "aic_multivariado": -117.9,
    "mape_pliegue_distancia": {"2.5": 7.9, "3.5": 8.4, "n_2.5": 40, "n_3.5": 39},
}


def escribir_metricas(tmp_path: Path, cambios: dict | None = None, quitar: tuple = ()) -> Path:
    m = {**METRICAS, **(cambios or {})}
    for k in quitar:
        m.pop(k)
    p = tmp_path / "metricas.json"
    p.write_text(json.dumps(m), encoding="utf-8")
    return p


def generar(tmp_path: Path, *extra: str) -> Path:
    metricas = escribir_metricas(tmp_path)
    out = tmp_path / "weight_model.json"
    assert mwb.main(["--metricas", str(metricas), "--out", str(out), *extra]) == 0
    return out


def test_claves_exactas_y_valores_redondeados(tmp_path):
    texto = generar(tmp_path).read_text(encoding="utf-8")
    bundle = json.loads(texto)
    assert list(bundle) == CLAVES
    assert list(bundle["interval"]) == CLAVES_INTERVAL
    assert bundle["a"] == round(METRICAS["a"], 4) == 0.41
    assert bundle["b"] == round(METRICAS["b"], 4) == 0.69
    iv = bundle["interval"]
    assert iv["sigma_log"] == round(SIGMA, 4)
    assert iv["t"] == round(T, 3)
    assert iv["n"] == N and isinstance(iv["n"], int)
    assert iv["factor"] == round(METRICAS["factor_ip"], 4)
    assert bundle["version"] == "campana_20260912"
    assert bundle["fuente"] == "n=40 vacas; campaña de calibración 12 sep 2026; MAPE LOO 6.50 % (IC95 5.1–8.0)"
    # indent=2, ensure_ascii=False y salto de línea final
    assert texto == json.dumps(bundle, indent=2, ensure_ascii=False) + "\n"
    assert "campaña" in texto and "\\u" not in texto


def test_factor_coherente_con_t_sigma_y_n(tmp_path):
    bundle = json.loads(generar(tmp_path).read_text(encoding="utf-8"))
    factor = bundle["interval"]["factor"]
    assert factor == round(math.exp(T * SIGMA * math.sqrt(1 + 1 / N)), 4)
    # peso_min = pred / factor, peso_max = pred × factor
    pred = bundle["a"] * 12000 ** bundle["b"]
    assert pred / factor < pred < pred * factor
    assert math.isclose(math.log(pred * factor) - math.log(pred / factor), 2 * math.log(factor))


def test_version_y_fuente_personalizadas(tmp_path):
    bundle = json.loads(generar(tmp_path, "--version", "prueba_v2", "--fuente", "texto propio").read_text())
    assert bundle["version"] == "prueba_v2"
    assert bundle["fuente"] == "texto propio"


def test_fuente_propia_no_exige_mape(tmp_path):
    metricas = escribir_metricas(tmp_path, quitar=("mape", "mape_ic95"))
    out = tmp_path / "weight_model.json"
    assert mwb.main(["--metricas", str(metricas), "--out", str(out), "--fuente", "texto"]) == 0
    assert json.loads(out.read_text())["fuente"] == "texto"


@pytest.mark.parametrize(
    "cambios, quitar, motivo",
    [
        ({"n": 2}, (), "'n'"),
        ({"a": 0}, (), "'a'"),
        ({"sigma_log": -0.01}, (), "'sigma_log'"),
        ({}, ("sigma_log",), "faltan claves"),
        ({}, ("mape_ic95",), "faltan claves"),
        ({"factor_ip": 1.5}, (), "'factor_ip'"),
    ],
)
def test_rechaza_metricas_invalidas(tmp_path, capsys, cambios, quitar, motivo):
    metricas = escribir_metricas(tmp_path, cambios, quitar)
    out = tmp_path / "weight_model.json"
    assert mwb.main(["--metricas", str(metricas), "--out", str(out)]) == 2
    assert not out.exists()
    assert motivo in capsys.readouterr().err


def test_cli_devuelve_2_al_sistema(tmp_path):
    metricas = escribir_metricas(tmp_path, {"n": 2})
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--metricas", str(metricas), "--out", str(tmp_path / "w.json")],
        capture_output=True, text=True,
    )
    assert r.returncode == 2
    assert "'n' debe ser un entero >= 3" in r.stderr
    assert not (tmp_path / "w.json").exists()


def test_bundle_actual_de_la_app_tiene_las_mismas_claves(tmp_path):
    """El bundle desplegado (solo lectura) y el generado comparten el nivel superior: la app lee ambos igual."""
    actual = json.loads(BUNDLE_APP.read_text(encoding="utf-8"))
    generado = json.loads(generar(tmp_path).read_text(encoding="utf-8"))
    assert list(actual) == list(generado) == CLAVES
