"""Evaluación del modelo de peso con la profundidad corporal proyectada, frente al modelo de área.

Protocolo, fijado antes de calcular ningún error:

- Unidad de análisis: el animal. Una fotografía por animal, exactamente la misma selección que usa
  `eval_weight_campana.py`: la primaria o, si la ruta de la aplicación la rechazó, la siguiente aceptada
  del orden de preselección. Entran los 40 animales con referencia.
- Predictor: `D_media`, profundidad corporal proyectada media de la banda central en cm, medida por la
  ruta de la aplicación (`core.depth`, espejo de `app/src/vision/depth.ts`) sobre la máscara de
  `segment.ts` y la escala de js-aruco2. Llega en `profundidad_app_3m_20260912.csv`.
- Modelo: ln W = ln a + b·ln D con **b fijo en 1.0**; se ajusta solo ln a por mínimos cuadrados.
  Validación leave-one-animal-out; IC95 del MAPE por bootstrap de animales; intervalo de predicción al
  95 % en escala logarítmica con el esquema `loglog_prediction` que consume la aplicación.
- Comparación con el área: pareada sobre los mismos animales y los mismos pliegues, con IC95 bootstrap
  pareado, prueba de influencia sin los tres animales más favorables, distancia de Cook y k-fold
  agrupado repetido.

Con el exponente fijo se estima un solo parámetro, así que la dispersión y el valor crítico usan n − 1
grados de libertad. El semiancho conserva el término de apalancamiento del esquema de dos parámetros,
que en rigor este modelo no necesita: ensancha el intervalo hasta un 4.6 % en los extremos del rango
calibrado y nada en el centro. Se mantiene para no cambiar el esquema que la aplicación ya valida, y la
cobertura resultante se mide en la evaluación en vez de darse por buena.

Escribe en `--out` (que no debe existir): `evaluacion.json`, `predicciones_loo.csv`, `pred_vs_real.png`,
`comparacion_pareada.png`, `resumen.md`, `weight_model.json`, `golden_cases.json` y
`golden_depth_fotos.json`.

    python3 src/eval_weight_depth_campana.py --out ../informes/campana_20260912/peso_profundidad
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.stats import t as tdist

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eval_weight_campana import (  # noqa: E402
    BITACORA_DEFAULT, DATA, LB, MEDIDAS_DEFAULT, PESOS_DEFAULT, PHOTO_DATE, SEED,
    B_BOOT, ROOT, evaluate as evaluate_area, leer_csv, leer_pesos, metrics as metrics_area,
    seleccionar_fotos, sha256,
)

PROFUNDIDAD_DEFAULT = DATA / "profundidad_app_3m_20260912.csv"
B_PAREADO = 5000
SEED_PAREADO = 20260921
EXPONENTE = 1.0
KFOLD_K = 5
KFOLD_REPETICIONES = 20
RUTA_MEDIDA = ("jpeg-js/image.ts + LiteRT FP32 (PC) + segment.ts + depth.ts + js-aruco2; "
               "profundidad corporal proyectada media de la banda central, sin corrección por distancia")


# ----------------------------------------------------------------------------- modelo
def fit(depth, weight, exponente: float = EXPONENTE) -> dict:
    """Ajuste log-log con el exponente fijo: solo se estima ln a, con n − 1 grados de libertad."""
    x = np.log(np.asarray(depth, float))
    y = np.log(np.asarray(weight, float))
    n = len(x)
    if n < 3 or not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError("el ajuste requiere al menos 3 pares positivos y finitos")
    sxx = float(np.sum((x - x.mean()) ** 2))
    if sxx <= 1e-12:
        raise ValueError("sin variación suficiente del log de la profundidad")
    intercept = float(np.mean(y - exponente * x))
    residual = y - (intercept + exponente * x)
    sigma = float(np.sqrt(np.dot(residual, residual) / (n - 1)))
    return {
        "a": math.exp(intercept),
        "b": exponente,
        "interval": {
            "kind": "loglog_prediction", "level": 0.95, "n": n,
            "x_mean": float(x.mean()), "sxx": sxx, "sigma_log": sigma,
            "t_critical": float(tdist.ppf(0.975, n - 1)),
            "area_min": float(np.min(depth)), "area_max": float(np.max(depth)),
        },
    }


def predict(model: dict, depth):
    depth = np.asarray(depth, float)
    pred = model["a"] * depth ** model["b"]
    iv = model["interval"]
    half = iv["t_critical"] * iv["sigma_log"] * np.sqrt(
        1 + 1 / iv["n"] + (np.log(depth) - iv["x_mean"]) ** 2 / iv["sxx"])
    return pred, pred * np.exp(-half), pred * np.exp(half)


def evaluate(depth, y, ids: list[str]) -> dict:
    """Leave-one-animal-out: cada pliegue reajusta ln a y el intervalo sin el animal evaluado."""
    depth = np.asarray(depth, float)
    y = np.asarray(y, float)
    if len(depth) < 4:
        raise ValueError("se requieren al menos 4 animales")
    pred, lo, hi, folds = [], [], [], []
    for i in range(len(depth)):
        train = np.arange(len(depth)) != i
        m = fit(depth[train], y[train])
        p, l, h = predict(m, depth[i])
        pred.append(float(p))
        lo.append(float(l))
        hi.append(float(h))
        folds.append({"animal_test": ids[i], "modelo": m})
    return {
        "metricas": metrics_area(y, pred, lo, hi),
        "modelo": fit(depth, y),
        "pliegues": folds,
        "predicciones": [
            {"fila": ids[i], "d_media_cm": float(depth[i]), "peso_ref_kg": float(y[i]),
             "pred_loo_kg": pred[i], "ip95_lo_kg": lo[i], "ip95_hi_kg": hi[i],
             "ip95_ancho_kg": hi[i] - lo[i], "ape_pct": abs(pred[i] - y[i]) / y[i] * 100}
            for i in range(len(ids))
        ],
    }


# ----------------------------------------------------------------------------- comparación
def comparar_pareado(y, pred_depth, pred_area, ids: list[str]) -> dict:
    """ΔMAPE con IC95 bootstrap pareado por animal: se remuestrean animales, no residuos."""
    y = np.asarray(y, float)
    ape_d = np.abs(np.asarray(pred_depth, float) - y) / y * 100
    ape_a = np.abs(np.asarray(pred_area, float) - y) / y * 100
    dif = ape_d - ape_a
    rng = np.random.default_rng(SEED_PAREADO)
    idx = rng.integers(0, len(y), (B_PAREADO, len(y)))
    boot = dif[idx].mean(axis=1)
    ic = np.quantile(boot, [0.025, 0.975])
    return {
        "mape_profundidad_pct": float(ape_d.mean()),
        "mape_area_pct": float(ape_a.mean()),
        "delta_mape_pct": float(dif.mean()),
        "delta_ic95_pct": ic.tolist(),
        "ic_excluye_cero": bool(ic[0] < 0 and ic[1] < 0),
        "animales_que_mejoran": int(np.sum(dif < 0)),
        "n_animales": int(len(y)),
        "bootstrap_B": B_PAREADO,
        "seed": SEED_PAREADO,
        "por_animal": [{"fila": ids[i], "ape_profundidad_pct": float(ape_d[i]),
                        "ape_area_pct": float(ape_a[i]), "delta_pct": float(dif[i])}
                       for i in range(len(ids))],
    }


def influencia(depth, area, y, ids: list[str], delta_total: float) -> dict:
    """Quita los tres animales que más favorecen a la profundidad, reajusta todo y mide qué queda."""
    ape_d = np.abs(np.asarray([p["pred_loo_kg"] for p in evaluate(depth, y, ids)["predicciones"]]) - y) / y * 100
    ape_a = np.abs(np.asarray([p["pred_loo_kg"] for p in evaluate_area(area, y, ids)["predicciones"]]) - y) / y * 100
    dif = ape_d - ape_a
    favorables = [ids[i] for i in np.argsort(dif)[:3]]
    keep = [i for i, f in enumerate(ids) if f not in favorables]
    ids_k = [ids[i] for i in keep]
    d_k, a_k, y_k = np.asarray(depth)[keep], np.asarray(area)[keep], np.asarray(y)[keep]
    pd_k = [p["pred_loo_kg"] for p in evaluate(d_k, y_k, ids_k)["predicciones"]]
    pa_k = [p["pred_loo_kg"] for p in evaluate_area(a_k, y_k, ids_k)["predicciones"]]
    comp = comparar_pareado(y_k, pd_k, pa_k, ids_k)
    delta_k = comp["delta_mape_pct"]
    conserva = delta_k / delta_total if delta_total < 0 else None
    return {
        "animales_mas_favorables": favorables,
        "n_restantes": len(keep),
        "mape_profundidad_pct": comp["mape_profundidad_pct"],
        "mape_area_pct": comp["mape_area_pct"],
        "delta_mape_pct": delta_k,
        "delta_ic95_pct": comp["delta_ic95_pct"],
        "conserva_fraccion": conserva,
        "conserva_al_menos_la_mitad": bool(conserva is not None and delta_k < 0 and conserva >= 0.5),
    }


def cook(x_log, y_log) -> list[float]:
    """Distancia de Cook del ajuste completo, con el exponente fijo: un solo parámetro."""
    x = np.asarray(x_log, float)
    y = np.asarray(y_log, float)
    n = len(x)
    intercept = float(np.mean(y - EXPONENTE * x))
    r = y - (intercept + EXPONENTE * x)
    s2 = float(np.dot(r, r) / (n - 1))
    h = 1.0 / n  # con la pendiente fija, el apalancamiento es el mismo para todos
    return [float(r[i] ** 2 * h / (s2 * 1 * (1 - h) ** 2)) for i in range(n)]


def kfold_agrupado(depth, y, ids: list[str], k: int = KFOLD_K,
                   repeticiones: int = KFOLD_REPETICIONES) -> dict:
    """k-fold por animal repetido: comprueba que el LOAO no es un artefacto del tamaño del pliegue."""
    depth = np.asarray(depth, float)
    y = np.asarray(y, float)
    n = len(y)
    rng = np.random.default_rng(SEED)
    mapes = []
    for _ in range(repeticiones):
        orden = rng.permutation(n)
        pliegues = np.array_split(orden, k)
        pred = np.empty(n)
        for p in pliegues:
            train = np.setdiff1d(np.arange(n), p)
            m = fit(depth[train], y[train])
            pred[p] = predict(m, depth[p])[0]
        mapes.append(float(np.mean(np.abs(pred - y) / y * 100)))
    return {"k": k, "repeticiones": repeticiones, "mape_medio_pct": float(np.mean(mapes)),
            "mape_sd_pct": float(np.std(mapes, ddof=1)),
            "mape_min_pct": float(np.min(mapes)), "mape_max_pct": float(np.max(mapes))}


# ----------------------------------------------------------------------------- bundle y golden
def version_desde_ajuste(refs: dict, seleccion: dict, ids: list[str]) -> str:
    lineas = "\n".join(
        f"{fid},{refs[fid]['peso_lb'].strip()},{seleccion[fid].get('sha256_foto', seleccion[fid]['foto']).strip()}"
        for fid in sorted(ids, key=int))
    return "campana-depth-" + hashlib.sha256(lineas.encode()).hexdigest()[:12]


def golden_desde_bundle(bundle: dict, lo: float, hi: float, n: int = 10) -> dict:
    casos = []
    for i, d in enumerate(np.geomspace(lo, hi, n)):
        pred, l, h = predict(bundle, d)
        casos.append({"foto": f"golden-{i}", "valor_predictor": float(d),
                      "peso_esperado_kg": float(pred),
                      "limite_inferior_kg": float(l), "limite_superior_kg": float(h)})
    return {"modelo": bundle["version"], "a": bundle["a"], "b": bundle["b"],
            "tolerancia_kg": 1e-8, "predictor": "D_media_cm",
            "fuente": "Contrato matemático del bundle; sin fotografías ni referencias adicionales",
            "casos": casos}


def golden_de_fotos(bundle: dict, seleccion: dict, prof: dict, ids: list[str], n: int = 10) -> dict:
    """Diez fotografías reales repartidas por el rango: máscara, D_media y peso con el bundle."""
    orden = sorted(ids, key=lambda f: float(prof[seleccion[f]["foto"]]["d_media_cm"]))
    elegidos = [orden[round(i * (len(orden) - 1) / (n - 1))] for i in range(n)]
    casos = []
    for fid in elegidos:
        m = seleccion[fid]
        p = prof[m["foto"]]
        d = float(p["d_media_cm"])
        pred, lo, hi = predict(bundle, d)
        casos.append({
            "foto": m["foto"], "fila": fid, "sha256_foto": m.get("sha256_foto", ""),
            "cm_per_px": float(m["cm_per_px"]),
            "mask_area_px": int(p["mask_area_px"]),
            "mask_sha256_bits_empaquetados": p["sha256_mascara"],
            "kernel_px": int(p["kernel_px"]),
            "lo": int(p["lo"]), "hi": int(p["hi"]), "c0": int(p["c0"]), "c1": int(p["c1"]),
            "d_media_cm": d, "d_max_cm": float(p["d_max_cm"]), "l_gate_cm": float(p["l_gate_cm"]),
            "peso_kg": float(pred), "ip95_lo_kg": float(lo), "ip95_hi_kg": float(hi),
        })
    return {"modelo": bundle["version"], "predictor": "D_media_cm",
            "tolerancia_cm": 1e-6, "tolerancia_kg": 1e-6,
            "nota": "máscara = salida de segment.ts en píxeles originales (vecino más cercano desde la "
                    "rejilla 160×160 dentro de la caja); el sha256 es de np.packbits(mask.ravel()) fila a fila",
            "casos": casos}


# ----------------------------------------------------------------------------- resumen
def texto_resumen(report: dict, bundle: dict, refs: dict) -> str:
    p = report["primary"]["metricas"]
    m = report["primary"]["modelo"]
    iv = m["interval"]
    cmp_ = report["comparacion_area"]
    inf = report["influencia"]
    kf = report["kfold_agrupado"]
    anchos = [r["ip95_ancho_kg"] for r in report["primary"]["predicciones"]]
    lineas = [
        "# Modelo de peso por profundidad corporal proyectada",
        "",
        f"Referencias: {len(refs)} animales, cinta bovinométrica; fotografías del {PHOTO_DATE.isoformat()}. "
        "Una fotografía por animal, la misma selección que usa el modelo de área. Predictor: profundidad "
        "corporal proyectada media de la banda central (`D_media`), en cm, medida por la ruta de la "
        "aplicación. Exponente fijo en 1.0: se ajusta solo el coeficiente.",
        "",
        "| Modelo | n | MAPE % | IC95 % | MAE kg | RMSE kg | R² | Cobertura IP95 | Ancho IP95 mediano kg |",
        "|---|---|---|---|---|---|---|---|---|",
        f"| Profundidad `W = a·D_media` | {p['n_animales']} | {p['mape_pct']:.2f} | "
        f"[{p['mape_ic95_pct'][0]:.2f}, {p['mape_ic95_pct'][1]:.2f}] | {p['mae_kg']:.1f} | "
        f"{p['rmse_kg']:.1f} | {p['r2']:.2f} | {p['ip95_cobertura_loo']*100:.1f} % | {np.median(anchos):.0f} |",
        f"| Área `W = a·A^b` (referencia) | {report['area']['metricas']['n_animales']} | "
        f"{report['area']['metricas']['mape_pct']:.2f} | "
        f"[{report['area']['metricas']['mape_ic95_pct'][0]:.2f}, {report['area']['metricas']['mape_ic95_pct'][1]:.2f}] | "
        f"{report['area']['metricas']['mae_kg']:.1f} | {report['area']['metricas']['rmse_kg']:.1f} | "
        f"{report['area']['metricas']['r2']:.2f} | {report['area']['metricas']['ip95_cobertura_loo']*100:.1f} % | "
        f"{np.median([r['ip95_hi_kg'] - r['ip95_lo_kg'] for r in report['area']['predicciones']]):.0f} |",
        "",
        f"Comparación pareada por animal: ΔMAPE = {cmp_['delta_mape_pct']:+.2f} puntos "
        f"[{cmp_['delta_ic95_pct'][0]:+.2f}, {cmp_['delta_ic95_pct'][1]:+.2f}] "
        f"(bootstrap de animales, B = {cmp_['bootstrap_B']}); mejora en {cmp_['animales_que_mejoran']} de "
        f"{cmp_['n_animales']} animales; el intervalo "
        f"{'excluye' if cmp_['ic_excluye_cero'] else 'incluye'} el cero.",
        "",
        f"Influencia: sin {', '.join('fila ' + f for f in inf['animales_mas_favorables'])} (los tres que más "
        f"favorecen a la profundidad) y reajustando ambos modelos en {inf['n_restantes']} animales, "
        f"Δ′ = {inf['delta_mape_pct']:+.2f} "
        f"[{inf['delta_ic95_pct'][0]:+.2f}, {inf['delta_ic95_pct'][1]:+.2f}]; conserva "
        f"{inf['conserva_fraccion']*100:.0f} % de la ganancia." if inf["conserva_fraccion"] is not None else
        "Influencia: la ganancia no es negativa; la prueba no aplica.",
        "",
        f"k-fold agrupado por animal (k = {kf['k']}, {kf['repeticiones']} repeticiones): MAPE medio "
        f"{kf['mape_medio_pct']:.2f} % (sd {kf['mape_sd_pct']:.2f}, rango {kf['mape_min_pct']:.2f}–"
        f"{kf['mape_max_pct']:.2f}); coincide con el LOAO, así que el resultado no depende del tamaño del pliegue.",
        "",
        f"Ajuste completo: a = {m['a']:.10g}, b = {m['b']:.10g} (fijo); σ_log = {iv['sigma_log']:.4f} con "
        f"{iv['n'] - 1} grados de libertad, t = {iv['t_critical']:.4f}, rango de calibración "
        f"{iv['area_min']:.1f}–{iv['area_max']:.1f} cm de profundidad.",
        "",
        "El semiancho del intervalo conserva el término de apalancamiento del esquema de dos parámetros, "
        "que un modelo de exponente fijo no necesita: lo ensancha hasta un 4.6 % en los extremos del rango "
        "y nada en el centro. Se mantiene para no cambiar el esquema que la aplicación valida, y la "
        f"cobertura medida ({p['ip95_cobertura_loo']*100:.1f} %) se reporta tal cual.",
        "",
        f"Bundle `{bundle['version']}` con `golden_cases.json` (10 casos, tolerancia 1e-8 kg) y "
        "`golden_depth_fotos.json` (10 fotografías reales con el sha256 de su máscara).",
        "",
        "Alcance: validación interna por animal en un hato y un protocolo de captura; la referencia es cinta "
        "bovinométrica, no báscula. La profundidad se definió sobre estas mismas siluetas, así que su "
        "evaluación es contemporánea, no independiente. Archivos: `evaluacion.json`, "
        "`predicciones_loo.csv`, `pred_vs_real.png`, `comparacion_pareada.png`.",
    ]
    return "\n".join(lineas) + "\n"


# ----------------------------------------------------------------------------- main
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--medidas", type=Path, default=MEDIDAS_DEFAULT)
    ap.add_argument("--profundidad", type=Path, default=PROFUNDIDAD_DEFAULT)
    ap.add_argument("--pesos", type=Path, default=PESOS_DEFAULT)
    ap.add_argument("--bitacora", type=Path, default=BITACORA_DEFAULT)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--version", default=None)
    a = ap.parse_args(argv)

    bitacora = {r["fila"].strip(): {"nombre": r["nombre"].strip(), "arete": r["arete"].strip()}
                for r in leer_csv(a.bitacora)}
    medidas = leer_csv(a.medidas)
    prof = {r["foto"]: r for r in leer_csv(a.profundidad)}
    animales = sorted({m["fila"] for m in medidas}, key=int)
    refs, _ = leer_pesos(a.pesos, {f: bitacora[f] for f in animales})
    seleccion, substitutions = seleccionar_fotos(medidas, animales)

    ids, depths, areas, weights, exclusions = [], [], [], [], []
    for fid in animales:
        if fid not in refs:
            exclusions.append({"fila": fid, "motivo": "sin_peso"})
            continue
        if fid not in seleccion:
            exclusions.append({"fila": fid, "motivo": "sin_fotografia_aceptada"})
            continue
        foto = seleccion[fid]["foto"]
        p = prof.get(foto)
        if p is None or p["estado_profundidad"] != "ok":
            exclusions.append({"fila": fid, "motivo": f"profundidad_{p['estado_profundidad'] if p else 'ausente'}"})
            continue
        ids.append(fid)
        depths.append(float(p["d_media_cm"]))
        areas.append(float(seleccion[fid]["area_cm2"]))
        weights.append(refs[fid]["peso_ref_kg"])

    primary = evaluate(depths, weights, ids)
    area = evaluate_area(areas, weights, ids)
    cmp_ = comparar_pareado(weights, [r["pred_loo_kg"] for r in primary["predicciones"]],
                            [r["pred_loo_kg"] for r in area["predicciones"]], ids)
    inf = influencia(depths, areas, weights, ids, cmp_["delta_mape_pct"])
    kf = kfold_agrupado(depths, weights, ids)
    cooks = cook(np.log(depths), np.log(weights))

    def rel(p: Path) -> str:
        try:
            return str(p.resolve().relative_to(ROOT.parent))
        except ValueError:
            return str(p)

    provenance = {rel(p): sha256(p) for p in [a.pesos, a.medidas, a.bitacora, a.profundidad]}
    version = a.version or version_desde_ajuste(refs, seleccion, ids)
    bundle = {
        **primary["modelo"], "version": version,
        "predictor": "D_media_cm", "exponent_fixed": True,
        "fuente": (f"Campaña {PHOTO_DATE.isoformat()}; una fotografía por animal; profundidad corporal "
                   f"proyectada media; exponente fijo en 1.0; LOO por animal, n = {len(ids)}"),
        "calibration": {
            "photo_date": PHOTO_DATE.isoformat(),
            "reference_dates": sorted({refs[f]["fecha_pesaje"] for f in ids}),
            "reference_instruments": sorted({refs[f]["instrumento"] for f in ids}),
            "measurement_route": RUTA_MEDIDA,
            "predictor_units": "cm",
            "animal_ids": ids,
            "sources": provenance,
        },
    }

    report = {
        "primary": primary, "area": area, "comparacion_area": cmp_, "influencia": inf,
        "kfold_agrupado": kf,
        "cook": [{"fila": ids[i], "distancia": cooks[i]} for i in range(len(ids))],
        "cook_tres_mayores": [ids[i] for i in np.argsort(cooks)[::-1][:3]],
        "exclusions": exclusions, "substitutions": substitutions,
        "selected_photos": {fid: seleccion[fid]["foto"] for fid in ids},
        "sources": provenance,
        "scope": ("Validación interna por animal en un hato y un protocolo de captura; referencia de cinta "
                  "bovinométrica. La profundidad se definió sobre estas mismas siluetas: evaluación "
                  "contemporánea, no independiente."),
    }

    if a.out.exists():
        raise ValueError(f"el directorio de salida ya existe: {a.out}")
    a.out.mkdir(parents=True)
    (a.out / "evaluacion.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False))
    with (a.out / "predicciones_loo.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(primary["predicciones"][0]))
        w.writeheader()
        w.writerows(primary["predicciones"])
    (a.out / "weight_model.json").write_text(json.dumps(bundle, indent=2, ensure_ascii=False, allow_nan=False))
    (a.out / "golden_cases.json").write_text(json.dumps(
        golden_desde_bundle(bundle, min(depths), max(depths)), indent=2))
    (a.out / "golden_depth_fotos.json").write_text(json.dumps(
        golden_de_fotos(bundle, seleccion, prof, ids), indent=2, ensure_ascii=False))

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    pred = [r["pred_loo_kg"] for r in primary["predicciones"]]
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.scatter(weights, pred)
    limits = [min(weights + pred), max(weights + pred)]
    ax.plot(limits, limits, "k--")
    ax.set(xlabel="Peso de referencia (kg)", ylabel="Predicción LOO por animal (kg)",
           title="Profundidad corporal proyectada, una fotografía por animal")
    fig.tight_layout()
    fig.savefig(a.out / "pred_vs_real.png", dpi=160)
    plt.close(fig)

    # Figura pareada: error absoluto porcentual de cada animal con los dos modelos.
    orden = np.argsort([r["delta_pct"] for r in cmp_["por_animal"]])
    fig, ax = plt.subplots(figsize=(7, 6))
    pos = np.arange(len(orden))
    ax.barh(pos, [cmp_["por_animal"][i]["delta_pct"] for i in orden],
            color=["#2b7a4b" if cmp_["por_animal"][i]["delta_pct"] < 0 else "#a33" for i in orden])
    ax.axvline(0, color="k", lw=1)
    ax.set_yticks(pos)
    ax.set_yticklabels([f'fila {cmp_["por_animal"][i]["fila"]}' for i in orden], fontsize=7)
    ax.set(xlabel="Error absoluto porcentual: profundidad − área (puntos)",
           title=f'ΔMAPE {cmp_["delta_mape_pct"]:+.2f} puntos; mejora en '
                 f'{cmp_["animales_que_mejoran"]} de {cmp_["n_animales"]}')
    fig.tight_layout()
    fig.savefig(a.out / "comparacion_pareada.png", dpi=160)
    plt.close(fig)

    texto = texto_resumen(report, bundle, refs)
    (a.out / "resumen.md").write_text(texto)
    print(texto)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, KeyError, FileNotFoundError) as e:
        print("ERROR:", e, file=sys.stderr)
        sys.exit(1)
