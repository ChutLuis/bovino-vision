"""Estadística complementaria del modelo de peso de la campaña de calibración.

Lee `evaluacion.json` de `eval_weight_campana.py` y calcula, sin reajustar el bundle ni elegir modelos: k-fold
agrupado por animal repetido (5 y 10 pliegues), bootstrap de a y b, predictor medio y exponentes fijos como
referencias, el modelo de la campaña piloto aplicado sin reajuste, Bland–Altman y CCC de Lin de la predicción LOO
frente a la cinta, cobertura del intervalo de predicción, las dos lecturas de cinta de junio (ruido de la
referencia) y el cambio de peso entre junio y septiembre en los animales presentes en ambas campañas.

    python src/weight_stats_campana.py [--evaluacion ../informes/campana_20260912/peso] [--out <dir>]
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
EVAL_DEFAULT = ROOT.parent / "informes/campana_20260912/peso"
REPESAJE = ROOT / "data/field/repesaje_1206/pesos_repesaje_12_06.csv"
CRUCE = ROOT / "data/field/campana_20260912/cruce_junio_20260912.csv"
SEED = 20260920
PILOTO = (0.375, 0.706)
LB = 0.45359237


def fit_loglog(area, y):
    b, a = np.polyfit(np.log(np.asarray(area, float)), np.log(np.asarray(y, float)), 1)
    return math.exp(a), float(b)


def predict(a, b, area):
    return a * np.asarray(area, float) ** b


def mape(y, p):
    y = np.asarray(y, float)
    p = np.asarray(p, float)
    return float(np.mean(np.abs(p - y) / y * 100))


def loo(area, y):
    area = np.asarray(area, float)
    y = np.asarray(y, float)
    n = len(y)
    p = np.empty(n)
    for i in range(n):
        m = np.arange(n) != i
        a, b = fit_loglog(area[m], y[m])
        p[i] = predict(a, b, area[i])
    return p


def kfold_repeated(area, y, k, reps, seed=SEED):
    area = np.asarray(area, float)
    y = np.asarray(y, float)
    n = len(y)
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(reps):
        folds = np.array_split(rng.permutation(n), k)
        p = np.empty(n)
        for f in folds:
            te = np.zeros(n, bool)
            te[f] = True
            a, b = fit_loglog(area[~te], y[~te])
            p[te] = predict(a, b, area[te])
        out.append(mape(y, p))
    return np.array(out)


def bootstrap_coef(area, y, B=5000, seed=SEED):
    area = np.asarray(area, float)
    y = np.asarray(y, float)
    n = len(y)
    rng = np.random.default_rng(seed)
    A, Bs = [], []
    for _ in range(B):
        idx = rng.integers(0, n, n)
        if len(set(idx.tolist())) < 4:
            continue
        a, b = fit_loglog(area[idx], y[idx])
        A.append(a)
        Bs.append(b)
    return np.array(A), np.array(Bs)


def loo_fixed_exponent(area, y, b):
    X = np.log(np.asarray(area, float))
    Y = np.log(np.asarray(y, float))
    n = len(Y)
    p = np.empty(n)
    for i in range(n):
        m = np.arange(n) != i
        p[i] = math.exp(float(np.mean(Y[m] - b * X[m])) + b * X[i])
    return p


def loo_mean(y):
    y = np.asarray(y, float)
    n = len(y)
    return np.array([y[np.arange(n) != i].mean() for i in range(n)])


def bland_altman(ref, pred):
    ref = np.asarray(ref, float)
    pred = np.asarray(pred, float)
    d = pred - ref
    bias = float(d.mean())
    sd = float(d.std(ddof=1)) if len(d) > 1 else 0.0
    lr = np.log(pred / ref)
    bp = float(lr.mean())
    sp = float(lr.std(ddof=1)) if len(d) > 1 else 0.0
    return {"n": int(len(d)), "bias_kg": bias, "sd_kg": sd, "loa_kg": [bias - 1.96 * sd, bias + 1.96 * sd],
            "bias_pct": 100 * (math.exp(bp) - 1),
            "loa_pct": [100 * (math.exp(bp - 1.96 * sp) - 1), 100 * (math.exp(bp + 1.96 * sp) - 1)]}


def lin_ccc(x, y):
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    mx, my = x.mean(), y.mean()
    cov = float(np.mean((x - mx) * (y - my)))
    return float(2 * cov / (x.var() + y.var() + (mx - my) ** 2))


def pearson(x, y):
    return float(np.corrcoef(np.asarray(x, float), np.asarray(y, float))[0, 1])


def texto(res: dict, n: int) -> str:
    P, K, Bc, S = res["primario"], res["kfold_agrupado_repetido"], res["bootstrap_coeficientes"], res["referencias_simples"]
    J, C, T, G = res["modelo_piloto_sin_reajuste"], res["concordancia"], res["cinta_junio_dos_lecturas"], res["cambio_junio_septiembre"]
    return f"""# Estadística complementaria del modelo de peso

| Medida | Valor |
|---|---|
| Animales | {n} |
| MAPE LOO por animal | {P['mape_pct']:.2f} %, IC95 [{P['mape_ic95_pct'][0]:.2f}, {P['mape_ic95_pct'][1]:.2f}] |
| H1a: MAPE puntual < 10 % / límite superior del IC95 < 10 % | {'sí' if P['h1a_punto_menor_10'] else 'no'} / {'sí' if P['h1a_ic95_superior_menor_10'] else 'no'} |
| a, b del ajuste completo | {P['a']:.4f}, {P['b']:.4f} |
| IC95 bootstrap de b (B = {Bc['B']}) | [{Bc['b_ic95'][0]:.3f}, {Bc['b_ic95'][1]:.3f}] |
| 5-fold agrupado × 2000 | media {K['5fold']['media_pct']:.2f} %, sd {K['5fold']['sd_pct']:.2f}, p2.5–p97.5 [{K['5fold']['p2_5']:.2f}, {K['5fold']['p97_5']:.2f}] |
| 10-fold agrupado × 2000 | media {K['10fold']['media_pct']:.2f} %, sd {K['10fold']['sd_pct']:.2f}, p2.5–p97.5 [{K['10fold']['p2_5']:.2f}, {K['10fold']['p97_5']:.2f}] |
| Predictor medio sin fotografía | {S['predictor_medio_mape_pct']:.2f} % |
| Exponente fijo 1.5 / 1.0 / libre | {S['exponente_1_5_mape_pct']:.2f} / {S['exponente_1_0_mape_pct']:.2f} / {S['exponente_libre_mape_pct']:.2f} % |
| Modelo del piloto (0.375·A^0.706) sin reajuste | MAPE {J['mape_pct']:.1f} %, predicho/real {J['cociente_medio_pred_real']:.3f}, subestima {J['subestima_n']}/{n}, sd log {J['sd_log']:.3f} |
| Bland–Altman, predicción LOO − cinta | sesgo {C['bias_kg']:+.1f} kg, LoA [{C['loa_kg'][0]:.1f}, {C['loa_kg'][1]:.1f}] kg; {C['bias_pct']:+.1f} %, LoA [{C['loa_pct'][0]:.1f}, {C['loa_pct'][1]:.1f}] % |
| CCC de Lin / r de Pearson | {C['ccc_lin']:.3f} / {C['r_pearson']:.3f} |
| Cobertura del IP95 en LOO | {P['cobertura_ip95_loo']*100:.1f} % ({P['fuera_ip95_n']} fuera) |
| sd del APE / semianchura aproximada del IC95 | {P['sd_ape_pp']:.1f} pp / ±{P['semianchura_ic95_aprox_pp']:.1f} pp |
| Cinta de junio, dos lecturas (n = {T['n']}) | diferencia absoluta media {T['dif_abs_media_pct']:.2f} %, máxima {T['dif_abs_max_pct']:.1f} %; {T['dif_abs_media_kg']:.1f} kg de media |
| Cambio junio → septiembre (n = {G['n']}) | medio {G['cambio_medio_kg']:+.1f} kg; absoluto medio {G['cambio_abs_medio_pct']:.1f} %; sd {G['sd_pct']:.1f} %; rango [{G['rango_pct'][0]:+.1f}, {G['rango_pct'][1]:+.1f}] % |

El modelo del piloto se aplica a las mismas fotografías seleccionadas sin reajustar: mide la transferencia entre
protocolos de colocación del marcador, no la calidad del ajuste nuevo. Las dos lecturas de cinta de junio (primera
el día del piloto, segunda el 12 de junio de 2026) incluyen cambio biológico y acotan por arriba el ruido de una
lectura. k-fold con k = n reproduce el LOO: {'sí' if K['kfold_k_igual_n_es_loo'] else 'no'}. Figuras:
`kfold_repetido.png`, `bland_altman.png`.
"""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--evaluacion", type=Path, default=EVAL_DEFAULT, help="directorio con evaluacion.json")
    ap.add_argument("--out", type=Path, default=None, help="directorio de salida (por defecto <evaluacion>/estadistica_extra); no debe existir")
    ap.add_argument("--repesaje", type=Path, default=REPESAJE)
    ap.add_argument("--cruce", type=Path, default=CRUCE)
    a = ap.parse_args(argv)
    out_dir = a.out or a.evaluacion / "estadistica_extra"
    ev = json.loads((a.evaluacion / "evaluacion.json").read_text())
    pr = ev["primary"]["predicciones"]
    area = np.array([r["area_cm2"] for r in pr])
    y = np.array([r["peso_ref_kg"] for r in pr])
    p_ev = np.array([r["pred_loo_kg"] for r in pr])
    lo = np.array([r["ip95_lo_kg"] for r in pr])
    hi = np.array([r["ip95_hi_kg"] for r in pr])
    n = len(y)
    p = loo(area, y)
    if not np.allclose(p, p_ev, rtol=1e-9, atol=1e-6):
        raise ValueError("el LOO propio difiere del evaluador")
    ape = np.abs(p - y) / y * 100
    a_, b_ = fit_loglog(area, y)
    met = ev["primary"]["metricas"]
    res = {"n_animales": n, "semilla": SEED, "loo_reproducido_igual_al_evaluador": True,
           "primario": {"mape_pct": mape(y, p), "mape_ic95_pct": met["mape_ic95_pct"], "a": a_, "b": b_,
                        "h1a_punto_menor_10": bool(mape(y, p) < 10), "h1a_ic95_superior_menor_10": bool(met["mape_ic95_pct"][1] < 10),
                        "sd_ape_pp": float(ape.std(ddof=1)), "semianchura_ic95_aprox_pp": float(1.96 * ape.std(ddof=1) / math.sqrt(n)),
                        "cobertura_ip95_loo": float(np.mean((y >= lo) & (y <= hi))), "fuera_ip95_n": int(np.sum(~((y >= lo) & (y <= hi)))),
                        "ape_max_pct": float(ape.max()), "ape_mediana_pct": float(np.median(ape))}}
    kf = {}
    muestras = {}
    for k in (5, 10):
        r = kfold_repeated(area, y, k, 2000)
        muestras[k] = r
        kf[f"{k}fold"] = {"reps": 2000, "media_pct": float(r.mean()), "sd_pct": float(r.std()), "p2_5": float(np.percentile(r, 2.5)),
                          "p97_5": float(np.percentile(r, 97.5)), "min": float(r.min()), "max": float(r.max())}
    kf["kfold_k_igual_n_es_loo"] = bool(abs(kfold_repeated(area, y, n, 1)[0] - mape(y, p)) < 1e-9)
    res["kfold_agrupado_repetido"] = kf
    A, Bs = bootstrap_coef(area, y)
    res["bootstrap_coeficientes"] = {"B": int(len(Bs)), "a_ic95": [float(np.percentile(A, 2.5)), float(np.percentile(A, 97.5))],
                                     "b_ic95": [float(np.percentile(Bs, 2.5)), float(np.percentile(Bs, 97.5))], "b_mediana": float(np.median(Bs))}
    res["referencias_simples"] = {"predictor_medio_mape_pct": mape(y, loo_mean(y)), "exponente_1_5_mape_pct": mape(y, loo_fixed_exponent(area, y, 1.5)),
                                  "exponente_1_0_mape_pct": mape(y, loo_fixed_exponent(area, y, 1.0)), "exponente_libre_mape_pct": mape(y, p)}
    pp = predict(*PILOTO, area)
    lr = np.log(y / pp)
    res["modelo_piloto_sin_reajuste"] = {"a": PILOTO[0], "b": PILOTO[1], "mape_pct": mape(y, pp), "mediana_ape_pct": float(np.median(np.abs(pp - y) / y * 100)),
                                         "cociente_medio_pred_real": float(np.mean(pp / y)), "subestima_n": int(np.sum(pp < y)),
                                         "factor_real_pred_geom": float(math.exp(lr.mean())), "sd_log": float(lr.std(ddof=1)),
                                         "interpretacion": "transferencia entre protocolos de colocación del marcador; no calidad del ajuste nuevo"}
    res["concordancia"] = {**bland_altman(y, p), "ccc_lin": lin_ccc(y, p), "r_pearson": pearson(y, p)}
    with a.repesaje.open(encoding="utf-8-sig", newline="") as f:
        rep = list(csv.DictReader(f))
    d = [(float(r["Weight (LB)"]), float(r["New_Weight"])) for r in rep if r["New_Weight"].strip()]
    dl = np.array([b2 - a1 for a1, b2 in d])
    rel = np.array([abs(b2 - a1) / a1 * 100 for a1, b2 in d])
    res["cinta_junio_dos_lecturas"] = {"n": len(d), "iguales": int(np.sum(dl == 0)), "dif_abs_media_pct": float(rel.mean()), "dif_abs_max_pct": float(rel.max()),
                                       "dif_abs_media_kg": float(np.mean(np.abs(dl)) * LB), "dif_abs_max_kg": float(np.max(np.abs(dl)) * LB),
                                       "sd_log_una_lectura": float(np.std(np.log([b2 / a1 for a1, b2 in d]), ddof=1) / math.sqrt(2)),
                                       "nota": "primera lectura el día del piloto, segunda el 12 de junio de 2026; incluye cambio biológico"}
    refs = ev["references"]
    ch, chp = [], []
    with a.cruce.open(encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            if r["peso_junio_lb"].strip() and r["fila"] in refs:
                j = float(r["peso_junio_lb"]) * LB
                s = float(refs[r["fila"]]["peso_ref_kg"])
                ch.append(s - j)
                chp.append((s - j) / j * 100)
    res["cambio_junio_septiembre"] = {"n": len(ch), "cambio_medio_kg": float(np.mean(ch)), "sd_kg": float(np.std(ch, ddof=1)),
                                      "cambio_abs_medio_pct": float(np.mean(np.abs(chp))), "sd_pct": float(np.std(chp, ddof=1)),
                                      "rango_pct": [float(min(chp)), float(max(chp))]}
    out_dir.mkdir(parents=True, exist_ok=False)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6, 4))
    for k in (5, 10):
        ax.hist(muestras[k], bins=40, alpha=0.6, label=f"{k}-fold agrupado, 2000 rep.")
    ax.axvline(mape(y, p), color="k", ls="--", label="LOO por animal")
    ax.set(xlabel="MAPE (%)", ylabel="repeticiones")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_dir / "kfold_repetido.png", dpi=160)
    plt.close(fig)
    ba = res["concordancia"]
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.scatter((y + p) / 2, p - y)
    for v, ls in ((ba["bias_kg"], "-"), (ba["loa_kg"][0], "--"), (ba["loa_kg"][1], "--")):
        ax.axhline(v, color="k", ls=ls)
    ax.set(xlabel="Media de referencia y predicción (kg)", ylabel="Predicción − referencia (kg)", title="Bland–Altman, predicción LOO frente a cinta")
    fig.tight_layout()
    fig.savefig(out_dir / "bland_altman.png", dpi=160)
    plt.close(fig)
    (out_dir / "estadistica_extra.json").write_text(json.dumps(res, indent=2, ensure_ascii=False, allow_nan=False))
    md = texto(res, n)
    (out_dir / "estadistica_extra.md").write_text(md)
    print(md)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, KeyError, FileNotFoundError) as e:
        print("ERROR:", e, file=sys.stderr)
        sys.exit(1)
