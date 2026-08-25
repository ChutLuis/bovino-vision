"""Evaluacion HONESTA y estable del modelo de peso (N chico, 1 foto por vaca).

Para N=34 con una foto por animal, leave-one-out (LOO) es mas estable que k=5:
cada vaca se predice con el modelo entrenado en las otras 33, y las metricas se
calculan SOBRE LAS 34 predicciones agrupadas (no promediando folds ruidosos).

Modelos (todos elegidos a priori, sin cherry-picking):
  - linear      : OLS sobre las 6 features (referencia simple)
  - ridge       : OLS regularizado (principiado para N chico + features colineales)
  - area_loglog : alometrico log(peso) ~ log(area_lateral)  (estandar en la literatura)
  - area_linear : solo area_lateral (la feature mas correlacionada)

Reporta MAPE, R2, RMSE pooled + IC bootstrap 95% del MAPE (2000 resamples por vaca).

    python3 src/eval_weight_fotos_hoy.py
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression, RidgeCV
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.metrics import r2_score

FEATURES = ["body_length_cm", "height_cm", "chest_depth_cm",
            "lateral_area_cm2", "aspect_ratio", "fill_ratio"]
RNG = np.random.default_rng(0)


def mape(y, p):
    return float(np.mean(np.abs((y - p) / y)) * 100)


def rmse(y, p):
    return float(np.sqrt(np.mean((y - p) ** 2)))


def loo_predict(make_model, X, y):
    """Leave-one-out: predice cada fila con modelo entrenado en el resto."""
    n = len(y)
    pred = np.zeros(n)
    for i in range(n):
        tr = np.arange(n) != i
        model = make_model()
        model.fit(X[tr], y[tr])
        pred[i] = model.predict(X[i:i + 1])[0]
    return pred


def loo_predict_loglog(area, y):
    n = len(y)
    pred = np.zeros(n)
    for i in range(n):
        tr = np.arange(n) != i
        b, a = np.polyfit(np.log(area[tr]), np.log(y[tr]), 1)  # log y = a + b log area
        pred[i] = np.exp(a + b * np.log(area[i]))
    return pred


def boot_ci_mape(y, p, n_boot=2000):
    n = len(y)
    vals = []
    for _ in range(n_boot):
        idx = RNG.integers(0, n, n)
        vals.append(mape(y[idx], p[idx]))
    lo, hi = np.percentile(vals, [2.5, 97.5])
    return float(lo), float(hi)


def main():
    df = pd.read_csv("data/field/features_fotos_hoy.csv").dropna(subset=FEATURES + ["weight_kg"])
    X = df[FEATURES].to_numpy(float)
    y = df["weight_kg"].to_numpy(float)
    area = df["lateral_area_cm2"].to_numpy(float)
    print(f"N usable = {len(y)} vacas (1 foto c/u) | peso {y.min():.0f}-{y.max():.0f} kg, "
          f"media {y.mean():.0f}, sd {y.std():.0f}\n")

    runs = {
        "linear (6 feat)":  loo_predict(lambda: make_pipeline(StandardScaler(), LinearRegression()), X, y),
        "ridge  (6 feat)":  loo_predict(lambda: make_pipeline(StandardScaler(), RidgeCV(alphas=np.logspace(-2, 3, 30))), X, y),
        "area log-log":     loo_predict_loglog(area, y),
        "area lineal":      loo_predict(lambda: make_pipeline(StandardScaler(), LinearRegression()), area.reshape(-1, 1), y),
    }

    print(f"{'modelo':18} {'MAPE%':>7} {'IC95 MAPE':>16} {'R2':>7} {'RMSE':>7}")
    print("-" * 60)
    best = None
    for name, pred in runs.items():
        mp, r2, rm = mape(y, pred), r2_score(y, pred), rmse(y, pred)
        lo, hi = boot_ci_mape(y, pred)
        flag_mape = "OK" if mp < 10 else "  "
        flag_r2 = "OK" if r2 > 0.85 else "  "
        print(f"{name:18} {mp:>6.2f}{flag_mape} [{lo:>5.1f},{hi:>5.1f}] {r2:>6.3f}{flag_r2} {rm:>6.1f}")
        if best is None or mp < best[1]:
            best = (name, mp, r2, rm, pred)

    # guarda predicho-vs-real del mejor por MAPE (para figura 4.4)
    name, mp, r2, rm, pred = best
    out = df[["orden", "cow_id", "weight_kg"]].copy()
    out["pred_kg"] = np.round(pred, 1)
    out["err_kg"] = np.round(pred - y, 1)
    out["ape_%"] = np.round(np.abs((pred - y) / y) * 100, 1)
    out.to_csv("data/field/pred_vs_real.csv", index=False)
    print(f"\nmejor por MAPE: {name}  ->  MAPE={mp:.2f}%  R2={r2:.3f}  RMSE={rm:.1f} kg")
    print("predicho-vs-real -> data/field/pred_vs_real.csv")
    print("\nH1a (MAPE<10% y R2>0.85): MAPE", "se cumple" if mp < 10 else "NO",
          "| R2", "se cumple" if r2 > 0.85 else "NO se cumple")


if __name__ == "__main__":
    raise SystemExit(main())
