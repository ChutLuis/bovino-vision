"""Ajuste y validación del modelo alométrico de peso con la campaña de calibración.

Unidad de análisis: la vaca. Cada animal aporta la mediana de sus fotos seleccionadas a 3 m
(`seleccionada_3m == 1`; con `--todas`, todas las fotos con `estado == ok`) y un peso de
referencia tomado de la bitácora (`peso_kg`, o la media de `peso_lb1`/`peso_lb2` × 0.45359237).

Se evalúan las dos áreas laterales del CSV de medidas (`lateral_area_cm2` cruda y
`lateral_area_cm2_corr`, corregida por paralaje). El modelo principal es el de menor MAPE en
validación cruzada dejando una vaca fuera (LOO); el otro se reporta como `alternativa`.

Métricas sobre las n predicciones LOO agrupadas: MAPE con IC 95 % bootstrap por vaca, R², RMSE y
MAE en kg. Del ajuste completo salen el intervalo de predicción log-log (`sigma_log`, `t`, `factor_ip`),
el AIC del alométrico y del multivariado (log área, longitud, altura, distancia), la robustez por
nivel de distancia (ajusta a 3.0 m, predice a 2.5 y 3.5 m), la repetibilidad entre fotos (ICC(1) del
log del peso predicho por foto, CV intra-vaca) y, si la bitácora trae dos pesadas, Bland–Altman.

Salidas en `--out`: `resultados_loo.csv`, `metricas.json`, `pred_vs_real.png`. Sin pesos en la
bitácora no escribe nada y termina con código 2.

    python src/eval_weight_campana.py
    python src/eval_weight_campana.py --todas --out /ruta/salida
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import r2_score

PIPELINE = Path(__file__).resolve().parents[1]
DATOS = PIPELINE / "data" / "field" / "campana_20260912"
FEATURES_DEFAULT = DATOS / "features_campana_20260912.csv"
BITACORA_DEFAULT = DATOS / "bitacora_campana_20260912.csv"
OUT_DEFAULT = PIPELINE.parent / "informes" / "campana_20260912"

LB_A_KG = 0.45359237
AREAS = ("lateral_area_cm2", "lateral_area_cm2_corr")
COVARIABLES = ("body_length_cm", "height_cm", "distancia_m")
NIVELES_PLIEGUE = (2.5, 3.5)
NIVEL_AJUSTE = 3.0


# ----------------------------------------------------------------------------- funciones base

def ajustar_loglog(area, peso):
    """Ajusta log(peso) = log(a) + b·log(area) por mínimos cuadrados y devuelve (a, b)."""
    area = np.asarray(area, float)
    peso = np.asarray(peso, float)
    b, intercepto = np.polyfit(np.log(area), np.log(peso), 1)
    return float(np.exp(intercepto)), float(b)


def predecir_loglog(a, b, area):
    return a * np.power(np.asarray(area, float), b)


def loo_loglog(area, peso):
    """Predicción LOO: cada vaca se predice con el alométrico ajustado sobre las demás."""
    area = np.asarray(area, float)
    peso = np.asarray(peso, float)
    n = len(peso)
    pred = np.zeros(n)
    for i in range(n):
        tr = np.arange(n) != i
        a, b = ajustar_loglog(area[tr], peso[tr])
        pred[i] = predecir_loglog(a, b, area[i])
    return pred


def mape(y, p):
    """Error porcentual absoluto medio, en %."""
    y = np.asarray(y, float)
    p = np.asarray(p, float)
    return float(np.mean(np.abs((y - p) / y)) * 100)


def ic_bootstrap_mape(y, p, n_boot=2000, seed=0):
    """IC 95 % del MAPE por bootstrap de vacas (percentiles 2.5 y 97.5) → (lo, hi)."""
    y = np.asarray(y, float)
    p = np.asarray(p, float)
    rng = np.random.default_rng(seed)
    n = len(y)
    idx = rng.integers(0, n, size=(n_boot, n))
    vals = np.mean(np.abs((y[idx] - p[idx]) / y[idx]), axis=1) * 100
    lo, hi = np.percentile(vals, [2.5, 97.5])
    return float(lo), float(hi)


def intervalo_prediccion(area, peso):
    """Intervalo de predicción 95 % del alométrico en escala log para un animal nuevo.

    sigma_log = sqrt(RSS / (n − 2)) del ajuste completo; t = t_{0.975, n−2};
    factor = exp(t · sigma_log · sqrt(1 + 1/n)). Uso: [pred / factor, pred × factor].
    """
    area = np.asarray(area, float)
    peso = np.asarray(peso, float)
    n = len(peso)
    a, b = ajustar_loglog(area, peso)
    resid = np.log(peso) - (np.log(a) + b * np.log(area))
    sigma_log = float(np.sqrt(np.sum(resid**2) / (n - 2)))
    t = float(stats.t.ppf(0.975, n - 2))
    factor = float(np.exp(t * sigma_log * np.sqrt(1 + 1 / n)))
    return {"sigma_log": sigma_log, "t": t, "n": int(n), "factor": factor}


def _ols(X, y):
    """Mínimos cuadrados con intercepto; devuelve (coeficientes, RSS). El primer coeficiente es el intercepto."""
    X = np.atleast_2d(np.asarray(X, float))
    if X.shape[0] != len(y):
        X = X.T
    D = np.column_stack([np.ones(len(y)), X])
    coef, *_ = np.linalg.lstsq(D, np.asarray(y, float), rcond=None)
    rss = float(np.sum((np.asarray(y, float) - D @ coef) ** 2))
    return coef, rss


def aic_ols(X, y) -> float:
    """AIC = n·ln(RSS/n) + 2k de la regresión OLS de y sobre las columnas de X más intercepto (k = p + 1)."""
    X = np.atleast_2d(np.asarray(X, float))
    if X.shape[0] != len(y):
        X = X.T
    n = len(y)
    _, rss = _ols(X, y)
    k = X.shape[1] + 1
    return float(n * np.log(rss / n) + 2 * k)


def icc1(grupos, valores) -> float:
    """ICC(1) por ANOVA de una vía (acuerdo entre medidas repetidas de un mismo grupo).

    MSB = SSB/(k−1), MSW = SSW/(N−k), n0 = (N − Σn_i²/N)/(k−1);
    ICC(1) = (MSB − MSW) / (MSB + (n0 − 1)·MSW). Admite grupos de tamaño distinto.
    """
    df = pd.DataFrame({"g": np.asarray(grupos), "v": np.asarray(valores, float)}).dropna()
    N = len(df)
    k = df["g"].nunique()
    if k < 2 or N <= k:
        return float("nan")
    media = df["v"].mean()
    por_grupo = df.groupby("g")["v"].agg(["size", "mean"])
    ssb = float(np.sum(por_grupo["size"] * (por_grupo["mean"] - media) ** 2))
    ssw = float(np.sum((df["v"] - df.groupby("g")["v"].transform("mean")) ** 2))
    msb = ssb / (k - 1)
    msw = ssw / (N - k)
    n0 = (N - np.sum(por_grupo["size"] ** 2) / N) / (k - 1)
    return float((msb - msw) / (msb + (n0 - 1) * msw))


# ----------------------------------------------------------------------------- datos

def peso_referencia(bitacora: pd.DataFrame) -> pd.Series:
    """Peso por fila: `peso_kg` o, si falta, la media de `peso_lb1`/`peso_lb2` presentes × 0.45359237."""
    kg = pd.to_numeric(bitacora["peso_kg"], errors="coerce")
    lb = bitacora[["peso_lb1", "peso_lb2"]].apply(pd.to_numeric, errors="coerce")
    desde_lb = lb.mean(axis=1, skipna=True) * LB_A_KG
    return kg.where(kg.notna(), desde_lb)


def leer_bitacora(ruta: Path) -> pd.DataFrame:
    b = pd.read_csv(ruta, dtype=str, keep_default_na=False)
    b = b.replace("", np.nan)
    b["fila"] = pd.to_numeric(b["fila"], errors="coerce").astype("Int64")
    b["peso_ref_kg"] = peso_referencia(b)
    return b


def leer_features(ruta: Path) -> pd.DataFrame:
    f = pd.read_csv(ruta, dtype={"arete": str, "estado": str, "foto": str, "nombre": str})
    f["fila"] = pd.to_numeric(f["fila"], errors="coerce").astype("Int64")
    for c in AREAS + COVARIABLES + ("nivel_distancia", "seleccionada_3m"):
        f[c] = pd.to_numeric(f[c], errors="coerce")
    return f


def filas_seleccionadas(f: pd.DataFrame, todas: bool) -> pd.DataFrame:
    ok = f[f["estado"] == "ok"]
    if todas:
        return ok
    return ok[ok["seleccionada_3m"] == 1]


def medianas_por_vaca(filas: pd.DataFrame) -> pd.DataFrame:
    cols = list(AREAS + COVARIABLES)
    g = filas.groupby("fila")
    med = g[cols].median()
    med["n_fotos"] = g.size()
    return med.reset_index()


def bland_altman(bitacora: pd.DataFrame):
    """Concordancia entre las dos pesadas de la bitácora, en kg; None si hay menos de dos vacas con ambas."""
    lb = bitacora[["peso_lb1", "peso_lb2"]].apply(pd.to_numeric, errors="coerce").dropna()
    if len(lb) < 2:
        return None
    d = (lb["peso_lb1"] - lb["peso_lb2"]).to_numpy(float) * LB_A_KG
    bias = float(np.mean(d))
    sd = float(np.std(d, ddof=1))
    return {"n": int(len(d)), "bias_kg": round(bias, 1), "sd_kg": round(sd, 1),
            "loa": [round(bias - 1.96 * sd, 1), round(bias + 1.96 * sd, 1)]}


# ----------------------------------------------------------------------------- evaluación

def evaluar_alometrico(area, peso, n_boot, seed):
    pred = loo_loglog(area, peso)
    a, b = ajustar_loglog(area, peso)
    lo, hi = ic_bootstrap_mape(peso, pred, n_boot=n_boot, seed=seed)
    ip = intervalo_prediccion(area, peso)
    return {
        "a": a, "b": b, "pred": pred,
        "mape": mape(peso, pred), "mape_ic95": [lo, hi],
        "r2": float(r2_score(peso, pred)),
        "rmse": float(np.sqrt(np.mean((peso - pred) ** 2))),
        "mae": float(np.mean(np.abs(peso - pred))),
        "sigma_log": ip["sigma_log"], "t": ip["t"], "factor_ip": ip["factor"],
        "aic_alometrico": aic_ols(np.log(area), np.log(peso)),
    }


def loo_multivariado(X, peso):
    """LOO del OLS log(peso) ~ columnas de X (log área y covariables), predicción en kg."""
    n = len(peso)
    logy = np.log(peso)
    pred = np.zeros(n)
    for i in range(n):
        tr = np.arange(n) != i
        coef, _ = _ols(X[tr], logy[tr])
        pred[i] = np.exp(coef[0] + X[i] @ coef[1:])
    return pred


def pliegue_distancia(f_ok: pd.DataFrame, pesos: pd.Series, area: str):
    """Ajusta con la mediana por vaca a 3.0 m y predice con la mediana por vaca a 2.5 y 3.5 m."""
    def mediana_nivel(nivel):
        sub = f_ok[np.isclose(f_ok["nivel_distancia"].astype(float), nivel)]
        med = sub.groupby("fila")[area].median()
        med = med[med.index.isin(pesos.index)].dropna()
        return med
    ajuste = mediana_nivel(NIVEL_AJUSTE)
    out = {}
    if len(ajuste) < 3:
        for nivel in NIVELES_PLIEGUE:
            out[f"{nivel}"] = None
            out[f"n_{nivel}"] = 0
        return out
    a, b = ajustar_loglog(ajuste.to_numpy(), pesos.loc[ajuste.index].to_numpy())
    for nivel in NIVELES_PLIEGUE:
        med = mediana_nivel(nivel)
        if len(med) == 0:
            out[f"{nivel}"] = None
        else:
            out[f"{nivel}"] = round(mape(pesos.loc[med.index].to_numpy(), predecir_loglog(a, b, med.to_numpy())), 2)
        out[f"n_{nivel}"] = int(len(med))
    return out


def repetibilidad(filas: pd.DataFrame, a: float, b: float, area: str):
    """ICC(1) del log del peso predicho por foto entre vacas y mediana del CV intra-vaca del peso predicho."""
    sub = filas.dropna(subset=[area])
    pred = predecir_loglog(a, b, sub[area].to_numpy())
    icc = icc1(sub["fila"].to_numpy(), np.log(pred))
    df = pd.DataFrame({"fila": sub["fila"].to_numpy(), "pred": pred})
    g = df.groupby("fila")["pred"]
    cv = (g.std(ddof=1) / g.mean() * 100).dropna()
    cv_med = float(cv.median()) if len(cv) else float("nan")
    return icc, cv_med


def redondear_alometrico(r: dict) -> dict:
    return {
        "a": round(r["a"], 4), "b": round(r["b"], 4),
        "mape": round(r["mape"], 2), "mape_ic95": [round(r["mape_ic95"][0], 2), round(r["mape_ic95"][1], 2)],
        "r2": round(r["r2"], 4), "rmse": round(r["rmse"], 1), "mae": round(r["mae"], 1),
        "sigma_log": round(r["sigma_log"], 4), "t": round(r["t"], 3), "factor_ip": round(r["factor_ip"], 4),
        "aic_alometrico": round(r["aic_alometrico"], 1),
    }


def graficar(peso, pred, factor, ruta: Path, titulo: str):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    lo = float(min(peso.min(), pred.min())) * 0.95
    hi = float(max(peso.max(), pred.max())) * 1.05
    x = np.linspace(lo, hi, 50)
    fig, ax = plt.subplots(figsize=(6, 6), dpi=150)
    ax.fill_between(x, x / factor, x * factor, color="#9DB7D5", alpha=0.25, linewidth=0,
                    label=f"IP 95 % (×/÷ {factor:.3f})")
    ax.plot(x, x, color="#6B7280", linewidth=1.5, linestyle="--", label="identidad")
    ax.scatter(peso, pred, s=42, color="#2B6CB0", edgecolor="white", linewidth=1.0, zorder=3,
               label="vaca (predicción LOO)")
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_aspect("equal")
    ax.set_xlabel("peso de referencia (kg)")
    ax.set_ylabel("peso predicho LOO (kg)")
    ax.set_title(titulo, fontsize=10)
    ax.grid(True, color="#E5E7EB", linewidth=0.8)
    ax.set_axisbelow(True)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    fig.tight_layout()
    fig.savefig(ruta)
    plt.close(fig)


# ----------------------------------------------------------------------------- programa

def construir_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Ajusta y valida el modelo alométrico de peso (LOO por vaca) con la campaña de calibración.")
    p.add_argument("--features", type=Path, default=FEATURES_DEFAULT, help="CSV de medidas por foto")
    p.add_argument("--bitacora", type=Path, default=BITACORA_DEFAULT, help="CSV de la bitácora con los pesos")
    p.add_argument("--out", type=Path, default=OUT_DEFAULT, help="directorio de salida")
    p.add_argument("--n-boot", type=int, default=2000, help="réplicas bootstrap para el IC del MAPE")
    p.add_argument("--seed", type=int, default=0, help="semilla del bootstrap")
    p.add_argument("--todas", action="store_true",
                   help="usar todas las fotos con estado ok en vez de las seleccionadas a 3 m")
    return p


def main(argv=None) -> int:
    args = construir_parser().parse_args(argv)

    bit = leer_bitacora(args.bitacora)
    if bit["peso_ref_kg"].notna().sum() == 0:
        print(f"sin pesos en la bitácora: peso_kg, peso_lb1 y peso_lb2 vacíos en las {len(bit)} filas",
              file=sys.stderr)
        return 2

    f = leer_features(args.features)
    filas = filas_seleccionadas(f, args.todas)
    med = medianas_por_vaca(filas)
    tabla = bit[["fila", "nombre", "peso_ref_kg", "arete"]].merge(med, on="fila", how="left")

    excluidas = []
    for _, r in tabla.iterrows():
        if pd.isna(r["peso_ref_kg"]):
            excluidas.append(f"{r['fila']} {r['nombre']}: sin peso")
        elif pd.isna(r["n_fotos"]) or pd.isna(r[AREAS[0]]):
            excluidas.append(f"{r['fila']} {r['nombre']}: sin fotos seleccionadas")
    for e in excluidas:
        print(f"excluida {e}", file=sys.stderr)

    datos = tabla.dropna(subset=["peso_ref_kg", "n_fotos"] + list(AREAS)).reset_index(drop=True)
    n = len(datos)
    if n < 3:
        print(f"solo {n} vacas con peso y fotos seleccionadas; se necesitan al menos 3", file=sys.stderr)
        return 2

    peso = datos["peso_ref_kg"].to_numpy(float)
    resultados = {area: evaluar_alometrico(datos[area].to_numpy(float), peso, args.n_boot, args.seed)
                  for area in AREAS}
    principal = min(AREAS, key=lambda k: resultados[k]["mape"])
    otra = [k for k in AREAS if k != principal][0]
    rp = resultados[principal]

    X_multi = np.column_stack([np.log(datos[principal].to_numpy(float))]
                              + [datos[c].to_numpy(float) for c in COVARIABLES])
    aic_multi = aic_ols(X_multi, np.log(peso))
    mape_multi = mape(peso, loo_multivariado(X_multi, peso))

    pesos_idx = datos.set_index("fila")["peso_ref_kg"]
    pliegue = pliegue_distancia(f[f["estado"] == "ok"], pesos_idx, principal)
    icc, cv_intra = repetibilidad(filas, rp["a"], rp["b"], principal)

    metricas = {
        "area": principal,
        **redondear_alometrico(rp),
        "n": int(n),
        "n_fotos": int(datos["n_fotos"].sum()),
        "seleccion": "todas_ok" if args.todas else "seleccionada_3m",
        "aic_multivariado": round(aic_multi, 1),
        "mape_multivariado": round(mape_multi, 2),
        "mape_pliegue_distancia": pliegue,
        "icc_repetibilidad": round(icc, 4) if np.isfinite(icc) else None,
        "cv_intra_pct": round(cv_intra, 2) if np.isfinite(cv_intra) else None,
        "bland_altman": bland_altman(bit),
        "alternativa": {"area": otra, **redondear_alometrico(resultados[otra])},
        "excluidas": excluidas,
    }

    args.out.mkdir(parents=True, exist_ok=True)
    loo = pd.DataFrame({
        "fila": datos["fila"].astype(int),
        "nombre": datos["nombre"],
        "peso_kg": np.round(peso, 1),
        "pred_kg": np.round(rp["pred"], 1),
        "ape_pct": np.round(np.abs(rp["pred"] - peso) / peso * 100, 2),
        "modelo": f"alometrico_{principal}",
    })
    loo.to_csv(args.out / "resultados_loo.csv", index=False)
    with open(args.out / "metricas.json", "w", encoding="utf-8") as fh:
        json.dump(metricas, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    graficar(peso, rp["pred"], rp["factor_ip"], args.out / "pred_vs_real.png",
             f"peso = {metricas['a']}·{principal}^{metricas['b']}  ·  n = {n}  ·  MAPE LOO {metricas['mape']:.2f} %")

    print(f"vacas: {n} ({metricas['n_fotos']} fotos, {metricas['seleccion']}); excluidas: {len(excluidas)}")
    print(f"modelo principal: {principal}  a = {metricas['a']}  b = {metricas['b']}")
    print(f"MAPE LOO {metricas['mape']:.2f} % (IC95 {metricas['mape_ic95'][0]:.2f}–{metricas['mape_ic95'][1]:.2f})"
          f"  R2 {metricas['r2']:.3f}  RMSE {metricas['rmse']:.1f} kg  MAE {metricas['mae']:.1f} kg")
    print(f"IP 95 %: sigma_log {metricas['sigma_log']}  t {metricas['t']}  factor {metricas['factor_ip']}")
    print(f"AIC alométrico {metricas['aic_alometrico']}  multivariado {metricas['aic_multivariado']}"
          f"  (MAPE multivariado {metricas['mape_multivariado']:.2f} %)")
    print(f"pliegue por distancia: {pliegue}")
    print(f"repetibilidad: ICC(1) {metricas['icc_repetibilidad']}  CV intra {metricas['cv_intra_pct']} %")
    print(f"alternativa {otra}: MAPE LOO {metricas['alternativa']['mape']:.2f} %")
    print(f"salidas en {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
