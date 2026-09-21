"""Contrato de `eval_weight_campana.py`.

(1) Ajuste log-log cerrado e intervalo de predicción iguales a la fórmula matricial.
(2) LOO por animal sin fuga: el animal evaluado no participa de su pliegue.
(3) Validación de referencias: unidades, faltantes, duplicados, fechas futuras e identidades.
(4) Recorrido sintético completo: sustitución de la primaria rechazada por la siguiente aceptada, exclusiones,
    secundario con los mismos animales, bundle y golden coherentes.
(5) Los datos de la campaña reproducen exactamente el bundle y el golden de `app/assets/model_bundle/`.
"""
import csv
import json
import math
from pathlib import Path

import numpy as np
import pytest
from scipy.stats import t as tdist

import eval_weight_campana as ev

ROOT = Path(__file__).resolve().parent.parent
APP_BUNDLE = ROOT.parent / "app/assets/model_bundle"


def test_fit_cerrado_e_intervalo():
    area = np.array([100, 200, 400, 800, 1600.0])
    m = ev.fit(area, 2 * area ** 0.5)
    assert m["a"] == pytest.approx(2, abs=1e-12)
    assert m["b"] == pytest.approx(0.5, abs=1e-12)
    p, lo, hi = ev.predict(m, 300)
    assert float(p) == pytest.approx(2 * math.sqrt(300), abs=1e-10)
    assert float(lo) <= float(p) <= float(hi)


def test_intervalo_igual_a_la_formula_matricial():
    area = np.array([8000, 11000, 14000, 18000, 21000, 26000.0])
    y = np.array([210, 260, 330, 360, 420, 470.0])
    x = np.log(area)
    X = np.column_stack([np.ones(len(x)), x])
    beta = np.linalg.lstsq(X, np.log(y), rcond=None)[0]
    residual = np.log(y) - X @ beta
    s2 = residual @ residual / (len(x) - 2)
    x0 = np.array([1, math.log(16000)])
    mu = x0 @ beta
    half = tdist.ppf(0.975, len(x) - 2) * math.sqrt(s2 * (1 + x0 @ np.linalg.inv(X.T @ X) @ x0))
    p, lo, hi = ev.predict(ev.fit(area, y), 16000)
    assert float(p) == pytest.approx(math.exp(mu), abs=1e-9)
    assert float(lo) == pytest.approx(math.exp(mu - half), abs=1e-9)
    assert float(hi) == pytest.approx(math.exp(mu + half), abs=1e-9)


def test_loo_sin_fuga_y_atipico_fuera():
    area = [100, 200, 300, 400, 500, 600]
    weights = [10, 14, 18, 20, 23, 90]
    ids = list("abcdef")
    r = ev.evaluate(area, weights, ids)
    for fold in r["pliegues"]:
        assert fold["animal_test"] not in fold["animales_train"]
    cambiado = ev.evaluate(area, weights[:-1] + [200], ids)
    assert r["predicciones"][-1]["pred_loo_kg"] == cambiado["predicciones"][-1]["pred_loo_kg"]
    assert r["metricas"]["n_animales"] == 6


def test_area_constante_rechazada():
    with pytest.raises(ValueError):
        ev.fit([1, 1, 1], [2, 3, 4])


def test_aic_mismo_n_y_k():
    x = np.array([[100 + i * 20, 10 + i + (i % 3), 8 + i * 0.5 + (i % 2)] for i in range(12)])
    r = ev.compare_aic(x, 2 * x[:, 0] ** 0.5 * np.exp(0.03 * np.sin(np.arange(12))))
    assert r["area"]["n"] == r["multivariado_bbox"]["n"] == 12
    assert r["area"]["k_incluye_varianza"] == 3
    assert r["selecciona_bundle"] is False


def _escribir(path: Path, rows, fields):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def test_leer_pesos_valida_unidades_faltantes_duplicados_e_identidad(tmp_path):
    ident = {"1": {"nombre": "A", "arete": "001"}, "2": {"nombre": "B", "arete": ""}}
    fields = ["fila", "nombre", "arete", "peso_lb", "fecha_pesaje", "instrumento", "fuente", "peso_lb2"]
    fila1 = {"fila": "1", "nombre": "A", "arete": "001", "peso_lb": "1000", "fecha_pesaje": "2026-09-20", "instrumento": "cinta", "fuente": "hoja"}
    p = tmp_path / "pesos.csv"
    _escribir(p, [fila1, {"fila": "2", "nombre": "B", "arete": ""}], fields)
    valid, missing = ev.leer_pesos(p, ident)
    assert valid["1"]["peso_ref_kg"] == pytest.approx(453.59237)
    assert valid["1"]["lectura2_kg"] is None
    assert missing == ["2"]
    _escribir(p, [fila1, {**fila1, "fila": "2", "nombre": "B", "arete": "", "peso_lb2": "1010"}], fields)
    valid, _ = ev.leer_pesos(p, ident)
    assert valid["2"]["peso_ref_kg"] == pytest.approx(1005 * 0.45359237)
    for malo in ([fila1, fila1], [{**fila1, "peso_lb": "nan"}], [{**fila1, "fecha_pesaje": "2099-01-01"}],
                 [{**fila1, "nombre": "Z"}], [{**fila1, "fuente": ""}], [{**fila1, "fila": "9"}]):
        _escribir(p, malo, fields)
        with pytest.raises(ValueError):
            ev.leer_pesos(p, ident)


def test_version_depende_de_pesos_y_fotografias_no_del_formato():
    refs_a = {"2": {"peso_lb": "810"}, "1": {"peso_lb": " 905 "}}
    refs_b = {"1": {"peso_lb": "905", "nombre": "otra cosa"}, "2": {"peso_lb": "810"}}
    sel = {"1": {"foto": "a.jpg", "sha256_foto": "aa"}, "2": {"foto": "b.jpg", "sha256_foto": "bb"}}
    ids = ["2", "1"]
    v = ev.version_desde_ajuste(refs_a, sel, ids)
    assert v == ev.version_desde_ajuste(refs_b, sel, ["1", "2"]) and v.startswith("campana-")
    assert ev.version_desde_ajuste({"1": {"peso_lb": "906"}, "2": {"peso_lb": "810"}}, sel, ids) != v
    otra_foto = {**sel, "2": {"foto": "c.jpg", "sha256_foto": "cc"}}
    assert ev.version_desde_ajuste(refs_a, otra_foto, ids) != v


def test_seleccionar_fotos_primaria_o_siguiente_aceptada():
    def m(fila, k, estado="ok", rev="aceptar"):
        return {"fila": fila, "foto": f"{fila}_{k}.jpg", "primaria": "1" if k == 1 else "0", "rango_3m": str(k),
                "estado": estado, "revision_visual": rev, "area_cm2": "100" if estado == "ok" else ""}
    medidas = [m("1", 1), m("1", 2), m("2", 1, "sin_vaca"), m("2", 2, "sin_vaca"), m("2", 3), m("3", 1, "ok", "excluir"), m("3", 2, "sin_marcador")]
    sel, sust = ev.seleccionar_fotos(medidas, ["1", "2", "3"])
    assert sel["1"]["foto"] == "1_1.jpg" and sel["2"]["foto"] == "2_3.jpg" and "3" not in sel
    assert sust == [{"fila": "2", "foto_primaria": "2_1.jpg", "motivo_primaria": "sin_vaca", "foto": "2_3.jpg", "rango_3m": 3}]
    with pytest.raises(ValueError):
        ev.seleccionar_fotos([m("1", 1), m("1", 1)], ["1"])


def _campana_sintetica(tmp_path: Path, n_vacas=12):
    bit, med, pesos = [], [], []
    for i in range(1, n_vacas + 1):
        nombre, arete = f"SINTETICA_{i}", f"T{i:03d}"
        bit.append({"fila": str(i), "nombre": nombre, "arete": arete, "categoria": "", "peso_lb1": "", "peso_lb2": "", "peso_kg": "", "telefono": "x", "notas": ""})
        area = 10000 + i * 1200
        peso_kg = 0.4 * area ** 0.7 * math.exp(0.035 * math.sin(i))
        if i != n_vacas:  # el último animal queda sin peso
            pesos.append({"fila": str(i), "nombre": nombre, "arete": arete, "peso_lb": f"{peso_kg / 0.45359237:.4f}",
                          "fecha_pesaje": "2026-09-20", "instrumento": "cinta", "fuente": "sintético"})
        for k in range(5):
            # la primaria del animal 2 se rechaza (entra su siguiente foto); el animal 3 no tiene ninguna aceptada
            estado = "sin_vaca" if (i == 2 and k == 0) or i == 3 else "ok"
            med.append({"foto": f"S_{i}_{k}.jpg", "fila": str(i), "nombre": nombre, "arete": arete, "primaria": "1" if k == 0 else "0",
                        "rango_3m": str(k + 1), "distancia_previa_m": "3.0", "estado": estado, "revision_visual": "aceptar",
                        "area_cm2": "" if estado != "ok" else f"{area * (1 + 0.01 * k):.4f}", "mask_area_px": "1", "cm_per_px": "0.1",
                        "marker_side_px": "150", "cow_dets": "1", "selected_confidence": "0.9",
                        "bbox_x0": "0", "bbox_y0": "0", "bbox_x1": str(1000 + i * 70 + (i % 3)), "bbox_y1": str(700 + i * 20 + (i % 2)), "sha256_foto": ""})
    _escribir(tmp_path / "bitacora.csv", bit, list(bit[0]))
    _escribir(tmp_path / "medidas.csv", med, list(med[0]))
    _escribir(tmp_path / "pesos.csv", pesos, list(pesos[0]))


def test_recorrido_sintetico(tmp_path):
    _campana_sintetica(tmp_path)
    out = tmp_path / "salida"
    code = ev.main(["--bitacora", str(tmp_path / "bitacora.csv"), "--medidas", str(tmp_path / "medidas.csv"),
                    "--pesos", str(tmp_path / "pesos.csv"), "--out", str(out)])
    assert code == 0
    rep = json.loads((out / "evaluacion.json").read_text())
    assert rep["primary"]["metricas"]["n_animales"] == 10  # 12 animales, uno sin peso y uno sin fotografía aceptada
    assert rep["secondary_median5"]["metricas"]["n_animales"] == 10
    assert {e["motivo"] for e in rep["exclusions"]} == {"sin_fotografia_aceptada", "sin_peso"}
    assert [(s["fila"], s["foto"], s["rango_3m"]) for s in rep["substitutions"]] == [("2", "S_2_1.jpg", 2)]
    assert rep["selected_photos"]["2"] == "S_2_1.jpg" and rep["selected_photos"]["1"] == "S_1_0.jpg"
    assert rep["primary"]["modelo"]["b"] == pytest.approx(0.7, abs=0.05)  # ley 0.4·A^0.7 con ruido lognormal
    bundle = json.loads((out / "weight_model.json").read_text())
    golden = json.loads((out / "golden_cases.json").read_text())
    assert bundle["interval"]["kind"] == "loglog_prediction" and golden["modelo"] == bundle["version"]
    for caso in golden["casos"]:
        p, lo, hi = ev.predict(bundle, caso["area_cm2"])
        assert float(p) == pytest.approx(caso["peso_esperado_kg"], abs=1e-9)
        assert float(lo) == pytest.approx(caso["limite_inferior_kg"], abs=1e-9)
        assert float(hi) == pytest.approx(caso["limite_superior_kg"], abs=1e-9)
    with pytest.raises(ValueError):  # no sobreescribe evidencia
        ev.main(["--bitacora", str(tmp_path / "bitacora.csv"), "--medidas", str(tmp_path / "medidas.csv"),
                 "--pesos", str(tmp_path / "pesos.csv"), "--out", str(out)])


def test_identidad_inconsistente_detiene(tmp_path):
    _campana_sintetica(tmp_path)
    rows = list(csv.DictReader((tmp_path / "medidas.csv").open(encoding="utf-8")))
    rows[0]["nombre"] = "OTRA"
    _escribir(tmp_path / "medidas.csv", rows, list(rows[0]))
    with pytest.raises(ValueError):
        ev.main(["--bitacora", str(tmp_path / "bitacora.csv"), "--medidas", str(tmp_path / "medidas.csv"),
                 "--pesos", str(tmp_path / "pesos.csv"), "--out", str(tmp_path / "s")])


def test_campana_reproduce_el_bundle_de_la_app(tmp_path):
    out = tmp_path / "campana"
    assert ev.main(["--out", str(out)]) == 0
    bundle = json.loads((out / "weight_model.json").read_text())
    app = json.loads((APP_BUNDLE / "weight_model.json").read_text())
    assert bundle["version"] == app["version"]
    assert bundle["a"] == pytest.approx(app["a"], abs=1e-12) and bundle["b"] == pytest.approx(app["b"], abs=1e-12)
    for k, v in app["interval"].items():
        assert bundle["interval"][k] == (pytest.approx(v, abs=1e-12) if isinstance(v, float) else v)
    golden = json.loads((out / "golden_cases.json").read_text())
    app_golden = json.loads((APP_BUNDLE / "golden_cases.json").read_text())
    assert [c["area_cm2"] for c in golden["casos"]] == pytest.approx([c["area_cm2"] for c in app_golden["casos"]], abs=1e-9)
    assert [c["peso_esperado_kg"] for c in golden["casos"]] == pytest.approx([c["peso_esperado_kg"] for c in app_golden["casos"]], abs=1e-9)
    rep = json.loads((out / "evaluacion.json").read_text())
    m = rep["primary"]["metricas"]
    assert m["n_animales"] == 40 and m["mape_pct"] == pytest.approx(7.7233, abs=1e-3)
    assert [s["fila"] for s in rep["substitutions"]] == ["7"] and rep["exclusions"] == []
    assert m["h1a_mape_menor_10"] and m["h1a_ic95_superior_menor_10"]
