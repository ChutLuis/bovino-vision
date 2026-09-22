"""Contrato de `repetibilidad_predictores_campana.py`.

(1) ICC(1) de una vía: acuerdo perfecto, caso balanceado contra la fórmula y casos sin estimación.
(2) Recorrido sintético: solo entran las fotografías aceptadas con profundidad medida; CSV y resumen coherentes.
"""
import csv
import json
import math

import numpy as np

import repetibilidad_predictores_campana as rp


def test_icc1_acuerdo_perfecto():
    assert rp.icc1([[1.0, 1.0, 1.0], [2.0, 2.0], [3.0, 3.0, 3.0, 3.0]]) == 1.0


def test_icc1_balanceado_contra_la_formula():
    grupos = [[1.0, 2.0], [3.0, 5.0], [10.0, 11.0]]
    medias = [np.mean(g) for g in grupos]
    media = np.mean(medias)
    msb = 2 * sum((m - media) ** 2 for m in medias) / (len(grupos) - 1)
    msw = sum(sum((v - np.mean(g)) ** 2 for v in g) for g in grupos) / (6 - 3)
    esperado = (msb - msw) / (msb + (2 - 1) * msw)
    assert math.isclose(rp.icc1(grupos), esperado, rel_tol=1e-12)


def test_icc1_sin_estimacion():
    assert rp.icc1([[1.0, 2.0]]) is None
    assert rp.icc1([[1.0], [2.0]]) is None


def _escribir(path, campos, filas):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(campos)
        w.writerows(filas)


def test_recorrido_sintetico(tmp_path):
    campos = ["foto", "fila", "nombre", "arete", "primaria", "rango_3m", "estado", "revision_visual", "area_cm2"]
    medidas = [
        ["a1.jpg", "1", "Uno", "11", "1", "1", "ok", "aceptar", "10000"],
        ["a2.jpg", "1", "Uno", "11", "0", "2", "ok", "aceptar", "10100"],
        ["a3.jpg", "1", "Uno", "11", "0", "3", "ok", "aceptar", "9900"],
        ["a4.jpg", "1", "Uno", "11", "0", "4", "sin_vaca", "", ""],          # rechazada por la ruta
        ["b1.jpg", "2", "Dos", "22", "1", "1", "ok", "aceptar", "16000"],
        ["b2.jpg", "2", "Dos", "22", "0", "2", "ok", "aceptar", "16000"],
        ["b3.jpg", "2", "Dos", "22", "0", "3", "ok", "aceptar", "16000"],
        ["b4.jpg", "2", "Dos", "22", "0", "4", "ok", "aceptar", "15000"],   # sin medida de profundidad
    ]
    profundidad = [
        ["a1.jpg", "1", "ok", "70"], ["a2.jpg", "1", "ok", "71"], ["a3.jpg", "1", "ok", "69"], ["a4.jpg", "1", "sin_mascara", ""],
        ["b1.jpg", "2", "ok", "60"], ["b2.jpg", "2", "ok", "60"], ["b3.jpg", "2", "ok", "60"],
    ]
    _escribir(tmp_path / "medidas.csv", campos, medidas)
    _escribir(tmp_path / "profundidad.csv", ["foto", "fila", "estado_profundidad", "d_media_cm"], profundidad)
    (tmp_path / "area.json").write_text(json.dumps({"a": 2.0, "b": 0.5}))
    (tmp_path / "prof.json").write_text(json.dumps({"a": 5.0, "b": 1.0}))
    out = tmp_path / "out"
    assert rp.main(["--medidas", str(tmp_path / "medidas.csv"), "--profundidad", str(tmp_path / "profundidad.csv"),
                    "--modelo-area", str(tmp_path / "area.json"), "--modelo-profundidad", str(tmp_path / "prof.json"),
                    "--out", str(out)]) == 0

    with (out / "repetibilidad_3m.csv").open(encoding="utf-8") as f:
        filas = list(csv.DictReader(f))
    assert [r["fila"] for r in filas] == ["1", "2"]
    assert [r["n_fotos"] for r in filas] == ["3", "3"]
    rango_uno = 2.0 * math.sqrt(10100) - 2.0 * math.sqrt(9900)
    assert math.isclose(float(filas[0]["rango_peso_area_kg"]), rango_uno, abs_tol=0.01)
    assert math.isclose(float(filas[0]["rango_peso_profundidad_kg"]), 5.0 * (71 - 69), abs_tol=1e-9)
    assert float(filas[1]["cv_peso_area_pct"]) == 0.0 and float(filas[1]["rango_peso_profundidad_kg"]) == 0.0

    texto = (out / "repetibilidad_3m.md").read_text()
    assert "ICC(1)" in texto and "| 6 | 2 |" in texto

    res = rp.resumir({"1": [10000.0, 10100.0, 9900.0], "2": [16000.0, 16000.0, 16000.0]}, 2.0, 0.5)
    assert 0.9 < res["icc1_log"] <= 1.0 and res["n_fotos"] == 6
