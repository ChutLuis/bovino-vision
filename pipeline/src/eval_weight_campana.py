"""Evaluación preespecificada del modelo alométrico de peso con la campaña de calibración.

Protocolo, fijado antes de recibir los pesos:

- Unidad de análisis: el animal. Una fotografía por animal: la primaria (la aceptada más cercana a 3.0 m,
  `primaria == 1` en `medidas_app_3m_20260912.csv`) o, si la ruta de la aplicación la rechazó, la siguiente
  fotografía aceptada del orden de preselección (`rango_3m`). Entran los 40 animales con referencia.
- Predictor: área lateral cruda en cm² medida por la ruta de la aplicación (jpeg-js, LiteRT FP32, `segment.ts`,
  js-aruco2), sin corrección por distancia.
- Modelo: ln W = ln a + b·ln A por mínimos cuadrados. Validación leave-one-out por animal; IC95 del MAPE por
  bootstrap de animales (B = 2000, semilla fija); intervalo de predicción al 95 % en escala logarítmica con el
  término de apalancamiento (`loglog_prediction`, el esquema que consume la aplicación).
- Secundarios, que no eligen el modelo: mediana de las fotografías aceptadas por animal, AIC del área frente a
  área + ancho + alto de la caja, repetibilidad entre fotografías (ICC(1) del log del área, CV del peso predicho).

Referencias: `pesos_20260920.csv` (fila, nombre, arete, peso_lb, fecha_pesaje, instrumento, fuente y, si la hay,
`peso_lb2`). Identidad validada contra la bitácora de la campaña. Escribe en `--out` (que no debe existir):
`evaluacion.json`, `predicciones_loo.csv`, `pred_vs_real.png`, `resumen.md` y, si a > 0 y b > 0,
`weight_model.json` y `golden_cases.json` listos para `app/assets/model_bundle/`.

    python src/eval_weight_campana.py --out ../informes/campana_20260912/peso
"""
from __future__ import annotations

import argparse
import csv
import datetime
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.stats import t as tdist

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/field/campana_20260912"
MEDIDAS_DEFAULT = DATA / "medidas_app_3m_20260912.csv"
PESOS_DEFAULT = DATA / "pesos_20260920.csv"
BITACORA_DEFAULT = DATA / "bitacora_campana_20260912.csv"
PHOTO_DATE = datetime.date(2026, 9, 12)
SEED = 20260919
B_BOOT = 2000
LB = 0.45359237
RUTA_MEDIDA = "jpeg-js/image.ts + LiteRT FP32 (PC) + segment.ts + js-aruco2; área cruda, sin corrección por distancia"


def leer_csv(path: Path) -> list[dict[str, str]]:
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# ----------------------------------------------------------------------------- modelo
def fit(area, weight) -> dict:
    """Ajuste log-log por mínimos cuadrados con los parámetros del intervalo de predicción."""
    x = np.log(np.asarray(area, float))
    y = np.log(np.asarray(weight, float))
    n = len(x)
    if n < 3 or not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError("el ajuste requiere al menos 3 pares positivos y finitos")
    sxx = float(np.sum((x - x.mean()) ** 2))
    if sxx <= 1e-12:
        raise ValueError("sin variación suficiente del log del área")
    b = float(np.dot(x - x.mean(), y - y.mean()) / sxx)
    intercept = float(y.mean() - b * x.mean())
    residual = y - (intercept + b * x)
    sigma = float(np.sqrt(np.dot(residual, residual) / (n - 2)))
    return {
        "a": math.exp(intercept),
        "b": b,
        "interval": {
            "kind": "loglog_prediction", "level": 0.95, "n": n,
            "x_mean": float(x.mean()), "sxx": sxx, "sigma_log": sigma,
            "t_critical": float(tdist.ppf(0.975, n - 2)),
            "area_min": float(np.min(area)), "area_max": float(np.max(area)),
        },
    }


def predict(model: dict, area):
    """Peso puntual y límites del intervalo de predicción al 95 %."""
    area = np.asarray(area, float)
    pred = model["a"] * area ** model["b"]
    iv = model["interval"]
    half = iv["t_critical"] * iv["sigma_log"] * np.sqrt(1 + 1 / iv["n"] + (np.log(area) - iv["x_mean"]) ** 2 / iv["sxx"])
    return pred, pred * np.exp(-half), pred * np.exp(half)


def metrics(y, pred, lo, hi) -> dict:
    y = np.asarray(y, float)
    pred = np.asarray(pred, float)
    ape = np.abs(pred - y) / y * 100
    rng = np.random.default_rng(SEED)
    boot = ape[rng.integers(0, len(y), (B_BOOT, len(y)))].mean(axis=1)
    denom = float(np.sum((y - y.mean()) ** 2))
    return {
        "n_animales": int(len(y)),
        "mape_pct": float(ape.mean()),
        "mape_ic95_pct": np.quantile(boot, [0.025, 0.975]).tolist(),
        "mae_kg": float(np.abs(pred - y).mean()),
        "rmse_kg": float(np.sqrt(np.mean((pred - y) ** 2))),
        "r2": float(1 - np.sum((pred - y) ** 2) / denom) if denom > 0 else None,
        "ip95_cobertura_loo": float(np.mean((y >= lo) & (y <= hi))),
        "h1a_mape_menor_10": bool(ape.mean() < 10),
        "h1a_ic95_superior_menor_10": bool(np.quantile(boot, 0.975) < 10),
        "bootstrap_B": B_BOOT,
        "seed": SEED,
    }


def evaluate(area, y, ids: list[str]) -> dict:
    """Leave-one-out por animal: cada pliegue reajusta a, b y el intervalo sin el animal evaluado."""
    area = np.asarray(area, float)
    y = np.asarray(y, float)
    if len(area) < 4:
        raise ValueError("se requieren al menos 4 animales para LOO con intervalo estimable")
    pred, lo, hi, folds = [], [], [], []
    for i in range(len(area)):
        train = np.arange(len(area)) != i
        m = fit(area[train], y[train])
        p, l, h = predict(m, area[i])
        pred.append(float(p))
        lo.append(float(l))
        hi.append(float(h))
        folds.append({"animal_test": ids[i], "animales_train": [ids[j] for j in range(len(ids)) if j != i], "modelo": m})
    return {
        "metricas": metrics(y, pred, lo, hi),
        "modelo": fit(area, y),
        "pliegues": folds,
        "predicciones": [
            {"fila": ids[i], "area_cm2": float(area[i]), "peso_ref_kg": float(y[i]), "pred_loo_kg": pred[i],
             "ip95_lo_kg": lo[i], "ip95_hi_kg": hi[i], "ape_pct": abs(pred[i] - y[i]) / y[i] * 100}
            for i in range(len(ids))
        ],
    }


def compare_aic(features, y) -> dict:
    """AIC gaussiano del área sola frente a área + ancho + alto de la caja; comparación, no selector."""
    y = np.log(np.asarray(y, float))
    x = np.asarray(features, float)
    if not np.isfinite(x).all() or np.any(x <= 0):
        return {"status": "no_evaluable_covariables"}
    out = {"status": "ok", "covariables": ["log_area_cm2", "log_ancho_bbox_cm", "log_alto_bbox_cm"], "selecciona_bundle": False}
    for name, columns in [("area", x[:, :1]), ("multivariado_bbox", x)]:
        X = np.column_stack([np.ones(len(y)), np.log(columns)])
        if len(y) <= X.shape[1] + 1 or np.linalg.matrix_rank(X) < X.shape[1]:
            out[name] = {"status": "rango_insuficiente"}
            continue
        coef = np.linalg.lstsq(X, y, rcond=None)[0]
        rss = float(np.sum((y - X @ coef) ** 2))
        k = X.shape[1] + 1
        if rss <= 0:
            out[name] = {"status": "residuo_cero"}
            continue
        out[name] = {"status": "ok", "aic": len(y) * (math.log(2 * math.pi) + 1 + math.log(rss / len(y))) + 2 * k,
                     "k_incluye_varianza": k, "n": int(len(y))}
    if all(out[n].get("status") == "ok" for n in ["area", "multivariado_bbox"]):
        out["delta_aic_multi_menos_area"] = out["multivariado_bbox"]["aic"] - out["area"]["aic"]
    return out


# ----------------------------------------------------------------------------- referencias
def leer_pesos(path: Path, identidades: dict[str, dict[str, str]]) -> tuple[dict, list[str]]:
    """Lee las referencias y valida identidad, unidad, fecha y procedencia. Devuelve (válidas, sin peso)."""
    seen, valid, missing, errors = set(), {}, [], []
    for r in leer_csv(path):
        fid = r.get("fila", "").strip()
        if fid in seen:
            errors.append(f"fila duplicada: {fid}")
            continue
        seen.add(fid)
        if fid not in identidades:
            errors.append(f"fila desconocida: {fid}")
            continue
        for k in ("nombre", "arete"):
            if r.get(k, "").strip() != identidades[fid][k]:
                errors.append(f"fila {fid}: {k} '{r.get(k, '')}' no coincide con la bitácora '{identidades[fid][k]}'")
        if not r.get("peso_lb", "").strip():
            missing.append(fid)
            continue
        try:
            w = float(r["peso_lb"])
            if not math.isfinite(w) or w <= 0:
                raise ValueError("peso no positivo o no finito")
            date = datetime.date.fromisoformat(r.get("fecha_pesaje", "").strip())
            if date > datetime.date.today():
                raise ValueError("fecha de pesaje futura")
            if not r.get("fuente", "").strip():
                raise ValueError("falta la fuente de la lectura")
            second = r.get("peso_lb2", "").strip()
            w2 = float(second) if second else None
            if w2 is not None and (not math.isfinite(w2) or w2 <= 0):
                raise ValueError("segunda lectura inválida")
            valid[fid] = {
                **r,
                "peso_ref_kg": LB * (w if w2 is None else (w + w2) / 2),
                "lectura1_kg": w * LB, "lectura2_kg": None if w2 is None else w2 * LB,
                "instrumento": r.get("instrumento", "").strip() or "no informado",
            }
        except (ValueError, KeyError) as e:
            errors.append(f"fila {fid}: {e}")
    missing += sorted(set(identidades) - seen, key=int)
    if errors:
        raise ValueError("\n".join(errors))
    return valid, sorted(missing, key=int)


def seleccionar_fotos(medidas: list[dict[str, str]], animales: list[str]) -> tuple[dict, list[dict]]:
    """Una fotografía por animal: la primaria si la ruta la aceptó; si no, la siguiente aceptada del orden de
    preselección (`rango_3m`). Devuelve (fila -> medida, sustituciones)."""
    aceptada = lambda m: m["estado"] == "ok" and m["revision_visual"] == "aceptar" and m["area_cm2"].strip()  # noqa: E731
    seleccion, sustituciones = {}, []
    for fid in animales:
        fotos = sorted((m for m in medidas if m["fila"] == fid), key=lambda m: int(m["rango_3m"]))
        primaria = [m for m in fotos if m["primaria"] == "1"]
        if len(primaria) != 1:
            raise ValueError(f"fila {fid}: debe tener exactamente una fotografía primaria")
        if aceptada(primaria[0]):
            seleccion[fid] = primaria[0]
            continue
        siguiente = next((m for m in fotos if aceptada(m)), None)
        if siguiente is None:
            continue
        motivo = primaria[0]["estado"] if primaria[0]["estado"] != "ok" else primaria[0]["revision_visual"]
        seleccion[fid] = siguiente
        sustituciones.append({"fila": fid, "foto_primaria": primaria[0]["foto"], "motivo_primaria": motivo,
                              "foto": siguiente["foto"], "rango_3m": int(siguiente["rango_3m"])})
    return seleccion, sustituciones


def version_desde_ajuste(refs: dict, seleccion: dict, ids: list[str]) -> str:
    """Identificador del ajuste: digest de las referencias (fila y libras) y de las fotografías que entran
    (fila, sha256 de la fotografía). Cambia si cambia un peso o una fotografía; no depende del formato."""
    lineas = "\n".join(f"{fid},{refs[fid]['peso_lb'].strip()},{seleccion[fid].get('sha256_foto', seleccion[fid]['foto']).strip()}"
                       for fid in sorted(ids, key=int))
    return "campana-" + hashlib.sha256(lineas.encode()).hexdigest()[:12]


def golden_desde_bundle(bundle: dict, area_min: float, area_max: float, n: int = 10) -> dict:
    grid = np.geomspace(area_min, area_max, n)
    casos = []
    for i, area in enumerate(grid):
        pred, lo, hi = predict(bundle, area)
        casos.append({"foto": f"golden-{i}", "area_cm2": float(area), "peso_esperado_kg": float(pred),
                      "limite_inferior_kg": float(lo), "limite_superior_kg": float(hi)})
    return {"modelo": bundle["version"], "a": bundle["a"], "b": bundle["b"], "tolerancia_kg": 1e-8,
            "fuente": "Contrato matemático del bundle; sin fotografías ni referencias adicionales", "casos": casos}


# ----------------------------------------------------------------------------- resumen
def texto_resumen(report: dict, bundle: dict | None, refs: dict) -> str:
    p = report["primary"]["metricas"]
    s = report["secondary_median5"]["metricas"]
    m = report["primary"]["modelo"]
    fechas = sorted({refs[f]["fecha_pesaje"] for f in refs})
    instrumentos = sorted({refs[f]["instrumento"] for f in refs})
    excl = "; ".join(f"fila {e['fila']} ({e['motivo']})" for e in report["exclusions"]) or "ninguna"
    sust = "; ".join(f"fila {s['fila']} ({s['motivo_primaria']} en la primaria; entra `{s['foto']}`, orden {s['rango_3m']})"
                     for s in report["substitutions"]) or "ninguna"
    lineas = [
        "# Modelo de peso de la campaña de calibración",
        "",
        f"Referencias: {len(refs)} animales, {', '.join(instrumentos)}, fecha {', '.join(fechas)}; fotografías del "
        f"{PHOTO_DATE.isoformat()}. Una fotografía por animal: la primaria o, si la ruta la rechazó, la siguiente aceptada "
        f"del orden de preselección. Sustituciones: {sust}. Exclusiones: {excl}.",
        "",
        "| Análisis | n | MAPE % | IC95 % | MAE kg | RMSE kg | R² | Cobertura IP95 |",
        "|---|---|---|---|---|---|---|---|",
        f"| Una fotografía por animal (primario) | {p['n_animales']} | {p['mape_pct']:.2f} | [{p['mape_ic95_pct'][0]:.2f}, {p['mape_ic95_pct'][1]:.2f}] | {p['mae_kg']:.1f} | {p['rmse_kg']:.1f} | {p['r2']:.2f} | {p['ip95_cobertura_loo']*100:.1f} % |",
        f"| Mediana de las fotografías aceptadas por animal (secundario) | {s['n_animales']} | {s['mape_pct']:.2f} | [{s['mape_ic95_pct'][0]:.2f}, {s['mape_ic95_pct'][1]:.2f}] | {s['mae_kg']:.1f} | {s['rmse_kg']:.1f} | {s['r2']:.2f} | {s['ip95_cobertura_loo']*100:.1f} % |",
        "",
        f"H1a (MAPE < 10 %): valor puntual {'sí' if p['h1a_mape_menor_10'] else 'no'}; límite superior del IC95 "
        f"{'sí' if p['h1a_ic95_superior_menor_10'] else 'no'}.",
        "",
        f"Ajuste completo del primario: a = {m['a']:.10g}, b = {m['b']:.10g}; σ_log = {m['interval']['sigma_log']:.4f}, "
        f"t = {m['interval']['t_critical']:.4f}, rango de calibración {m['interval']['area_min']:.0f}–{m['interval']['area_max']:.0f} cm².",
    ]
    aic = report["aic_secundario"]
    if aic.get("status") == "ok" and "delta_aic_multi_menos_area" in aic:
        lineas.append(f"AIC área {aic['area']['aic']:.1f} frente a área + caja {aic['multivariado_bbox']['aic']:.1f} "
                      f"(Δ = {aic['delta_aic_multi_menos_area']:.1f}); comparación secundaria, no elige el bundle.")
    rep = report["repeatability"]
    if rep["icc1_log_area"] is not None:
        cvs = [c["cv_pct"] for c in rep["cv_por_animal"]]
        lineas.append(f"Repetibilidad entre fotografías del mismo animal: ICC(1) del log del área {rep['icc1_log_area']:.3f}; "
                      f"CV del peso predicho mediana {np.median(cvs):.2f} %, máximo {max(cvs):.2f} %.")
    if bundle is not None:
        lineas += ["", f"Bundle `{bundle['version']}` escrito con `golden_cases.json` (10 casos, tolerancia 1e-8 kg)."]
    lineas += ["", "Alcance: validación interna por animal en un hato y un protocolo de captura; la referencia es cinta "
               "bovinométrica, no báscula. Archivos: `evaluacion.json`, `predicciones_loo.csv`, `pred_vs_real.png`."]
    return "\n".join(lineas) + "\n"


# ----------------------------------------------------------------------------- main
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--medidas", type=Path, default=MEDIDAS_DEFAULT, help="CSV de medidas de la ruta de la app (200 fotos a 3 m)")
    ap.add_argument("--pesos", type=Path, default=PESOS_DEFAULT, help="CSV de referencias por fila")
    ap.add_argument("--bitacora", type=Path, default=BITACORA_DEFAULT, help="bitácora canónica (fila, nombre, arete)")
    ap.add_argument("--out", type=Path, required=True, help="directorio de salida; no debe existir")
    ap.add_argument("--version", default=None, help="identificador del bundle (por defecto, digest de las referencias)")
    ap.add_argument("--solo-validar", action="store_true", help="valida referencias e identidades y termina")
    a = ap.parse_args(argv)

    bitacora = {r["fila"].strip(): {"nombre": r["nombre"].strip(), "arete": r["arete"].strip()} for r in leer_csv(a.bitacora)}
    medidas = leer_csv(a.medidas)
    for m in medidas:
        ident = bitacora.get(m["fila"])
        if ident is None or ident["nombre"] != m["nombre"] or ident["arete"] != m["arete"]:
            raise ValueError(f"{m['foto']}: identidad de la fila {m['fila']} no coincide con la bitácora")
    animales = sorted({m["fila"] for m in medidas}, key=int)
    refs, missing = leer_pesos(a.pesos, {f: bitacora[f] for f in animales})
    if not refs:
        print("sin referencias: no se ajusta ni se escribe nada", file=sys.stderr)
        return 2
    if a.solo_validar:
        print(json.dumps({"recibidos": len(refs), "sin_peso": missing}, ensure_ascii=False))
        return 0

    seleccion, substitutions = seleccionar_fotos(medidas, animales)
    ids, areas, weights, exclusions = [], [], [], []
    for fid in animales:
        if fid not in refs:
            exclusions.append({"fila": fid, "motivo": "sin_peso"})
            continue
        if fid not in seleccion:
            exclusions.append({"fila": fid, "motivo": "sin_fotografia_aceptada"})
            continue
        ids.append(fid)
        areas.append(float(seleccion[fid]["area_cm2"]))
        weights.append(refs[fid]["peso_ref_kg"])
    primary = evaluate(areas, weights, ids)

    covariates = []
    for fid in ids:
        m = seleccion[fid]
        try:
            s = float(m["cm_per_px"])
            covariates.append([float(m["area_cm2"]), (float(m["bbox_x1"]) - float(m["bbox_x0"])) * s,
                               (float(m["bbox_y1"]) - float(m["bbox_y0"])) * s])
        except ValueError:
            covariates.append([float(m["area_cm2"]), float("nan"), float("nan")])
    aic = compare_aic(covariates, weights)

    # Secundarios sobre exactamente los mismos animales para conservar denominadores comparables.
    aceptadas = {fid: [m for m in medidas if m["fila"] == fid and m["estado"] == "ok" and m["revision_visual"] == "aceptar"] for fid in ids}
    secondary = evaluate([float(np.median([float(m["area_cm2"]) for m in aceptadas[fid]])) for fid in ids], weights, ids)
    repeat, cvs = [], []
    for fid in ids:
        fold = next(f for f in primary["pliegues"] if f["animal_test"] == fid)
        vals = []
        for m in aceptadas[fid]:
            pred, lo, hi = predict(fold["modelo"], float(m["area_cm2"]))
            vals.append(float(pred))
            repeat.append({"fila": fid, "foto": m["foto"], "primaria": m["primaria"] == "1", "area_cm2": float(m["area_cm2"]),
                           "pred_loo_animal_kg": float(pred), "peso_ref_kg": refs[fid]["peso_ref_kg"], "lo": float(lo), "hi": float(hi)})
        if len(vals) > 1:
            cvs.append({"fila": fid, "n": len(vals), "cv_pct": float(np.std(vals, ddof=1) / np.mean(vals) * 100)})
    groups = [[math.log(float(m["area_cm2"])) for m in aceptadas[fid]] for fid in ids]
    N, k = sum(map(len, groups)), len(groups)
    mean = np.mean([v for g in groups for v in g])
    msb = sum(len(g) * (np.mean(g) - mean) ** 2 for g in groups) / (k - 1)
    msw = sum(sum((v - np.mean(g)) ** 2 for v in g) for g in groups) / (N - k) if N > k else None
    n0 = (N - sum(len(g) ** 2 for g in groups) / N) / (k - 1)
    icc = float((msb - msw) / (msb + (n0 - 1) * msw)) if msw is not None and msb + (n0 - 1) * msw > 0 else None

    paired = [r for r in refs.values() if r["lectura2_kg"] is not None]
    ba = None
    if len(paired) >= 2:
        dif = np.array([r["lectura2_kg"] - r["lectura1_kg"] for r in paired])
        bias, sd = float(dif.mean()), float(dif.std(ddof=1))
        ba = {"n": len(dif), "bias_kg": bias, "loa_kg": [bias - 1.96 * sd, bias + 1.96 * sd]}

    def rel(p: Path) -> str:
        try:
            return str(p.resolve().relative_to(ROOT.parent))
        except ValueError:
            return str(p)

    provenance = {rel(p): sha256(p) for p in [a.pesos, a.medidas, a.bitacora]}
    version = a.version or version_desde_ajuste(refs, seleccion, ids)
    bundle = {
        **primary["modelo"], "version": version,
        "fuente": f"Campaña {PHOTO_DATE.isoformat()}; una fotografía por animal; LOO por animal, n = {len(ids)}; referencias con fecha declarada",
        "calibration": {
            "photo_date": PHOTO_DATE.isoformat(),
            "reference_dates": sorted({refs[f]["fecha_pesaje"] for f in ids}),
            "reference_instruments": sorted({refs[f]["instrumento"] for f in ids}),
            "measurement_route": RUTA_MEDIDA,
            "animal_ids": ids,
            "sources": provenance,
        },
    }
    deployable = bundle["a"] > 0 and bundle["b"] > 0 and all(math.isfinite(bundle[x]) for x in ["a", "b"])
    report = {
        "primary": primary, "secondary_median5": secondary, "exclusions": exclusions, "substitutions": substitutions,
        "selected_photos": {fid: seleccion[fid]["foto"] for fid in ids},
        "references": {f: {k: v for k, v in refs[f].items()} for f in refs},
        "repeated_photo_predictions": repeat, "repeatability": {"icc1_log_area": icc, "cv_por_animal": cvs},
        "bland_altman": ba, "aic_secundario": aic, "bundle_deployable": deployable, "sources": provenance,
        "scope": "Validación interna por animal en un hato y un protocolo de captura; referencias con fecha e instrumento declarados. No es validación externa.",
    }
    if a.out.exists():
        raise ValueError(f"el directorio de salida ya existe: {a.out}")
    a.out.mkdir(parents=True)
    (a.out / "evaluacion.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False))
    with (a.out / "predicciones_loo.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(primary["predicciones"][0]))
        w.writeheader()
        w.writerows(primary["predicciones"])
    if deployable:
        (a.out / "weight_model.json").write_text(json.dumps(bundle, indent=2, ensure_ascii=False, allow_nan=False))
        golden = golden_desde_bundle(bundle, min(areas), max(areas))
        (a.out / "golden_cases.json").write_text(json.dumps(golden, indent=2))

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    pred = [r["pred_loo_kg"] for r in primary["predicciones"]]
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.scatter(weights, pred)
    limits = [min(weights + pred), max(weights + pred)]
    ax.plot(limits, limits, "k--")
    ax.set(xlabel="Peso de referencia (kg)", ylabel="Predicción LOO por animal (kg)", title="Una fotografía por animal")
    fig.tight_layout()
    fig.savefig(a.out / "pred_vs_real.png", dpi=160)
    plt.close(fig)
    texto = texto_resumen(report, bundle if deployable else None, refs)
    (a.out / "resumen.md").write_text(texto)
    print(texto)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, KeyError, FileNotFoundError) as e:
        print("ERROR:", e, file=sys.stderr)
        sys.exit(1)
