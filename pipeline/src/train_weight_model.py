"""Train the image-morphometry -> live-weight regression model.

Input: a CSV with one row per labeled sample. Required columns:
    cow_id              individual animal id (ear tag) — used for grouping
    weight_kg           ground-truth weight (scale, or cinta bovinométrica)
  + one column per feature (the morphometry fields), e.g.:
    body_length_cm, height_cm, chest_depth_cm, lateral_area_cm2,
    aspect_ratio, fill_ratio
  Optionally:
    thoracic_perimeter_cm   tape-measured girth (enables the barymetric baseline)

Validation: GroupKFold by cow_id (k=5 default). Grouping by ANIMAL prevents
leakage — multiple photos of the same cow never straddle train/test, which is
exactly the stratified-by-animal scheme the thesis methodology specifies.

Reports MAPE, R², RMSE per fold and averaged. Saves the model fit on all data.

Example:
    python3 src/train_weight_model.py --csv data/features.csv --out models/weight_model.joblib
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

DEFAULT_FEATURES = [
    "body_length_cm",
    "height_cm",
    "chest_depth_cm",
    "lateral_area_cm2",
    "aspect_ratio",
    "fill_ratio",
]


def mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.mean(np.abs((y_true - y_pred) / y_true)) * 100.0)


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def build_model(kind: str):
    from sklearn.linear_model import LinearRegression
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler, PolynomialFeatures

    if kind == "linear":
        return make_pipeline(StandardScaler(), LinearRegression())
    if kind == "poly2":
        return make_pipeline(StandardScaler(), PolynomialFeatures(degree=2), LinearRegression())
    if kind == "rf":
        return RandomForestRegressor(n_estimators=300, random_state=0, n_jobs=-1)
    raise ValueError(f"unknown model kind: {kind}")


def cross_validate(X, y, groups, kind: str, n_splits: int):
    from sklearn.model_selection import GroupKFold
    from sklearn.metrics import r2_score

    n_groups = len(set(groups))
    n_splits = min(n_splits, n_groups)
    gkf = GroupKFold(n_splits=n_splits)

    fold_metrics = []
    for fold, (tr, te) in enumerate(gkf.split(X, y, groups=groups), start=1):
        model = build_model(kind)
        model.fit(X[tr], y[tr])
        pred = model.predict(X[te])
        m = {
            "fold": fold,
            "n_test": len(te),
            "mape": mape(y[te], pred),
            "r2": float(r2_score(y[te], pred)) if len(te) > 1 else float("nan"),
            "rmse": rmse(y[te], pred),
        }
        fold_metrics.append(m)
    return fold_metrics, n_splits


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Train morphometry -> weight regression")
    parser.add_argument("--csv", required=True, help="Feature table CSV")
    parser.add_argument("--out", default="models/weight_model.joblib", help="Output model path")
    parser.add_argument("--model", default="linear", choices=["linear", "poly2", "rf"])
    parser.add_argument("--features", nargs="*", default=DEFAULT_FEATURES)
    parser.add_argument("--target", default="weight_kg")
    parser.add_argument("--group", default="cow_id")
    parser.add_argument("--folds", type=int, default=5)
    args = parser.parse_args(argv)

    import pandas as pd
    import joblib

    df = pd.read_csv(args.csv)
    missing = [c for c in args.features + [args.target, args.group] if c not in df.columns]
    if missing:
        parser.error(f"CSV missing columns: {missing}")

    df = df.dropna(subset=args.features + [args.target, args.group])
    X = df[args.features].to_numpy(dtype=float)
    y = df[args.target].to_numpy(dtype=float)
    groups = df[args.group].to_numpy()

    n_cows = len(set(groups))
    print(f"Loaded {len(df)} samples from {n_cows} cows ({args.model} model)")
    print(f"Features: {args.features}")

    fold_metrics, used_splits = cross_validate(X, y, groups, args.model, args.folds)
    print(f"\nGroupKFold by '{args.group}' — {used_splits} folds:")
    print(f"{'fold':>4} {'n_test':>7} {'MAPE%':>8} {'R2':>8} {'RMSE':>8}")
    for m in fold_metrics:
        print(f"{m['fold']:>4} {m['n_test']:>7} {m['mape']:>8.2f} {m['r2']:>8.3f} {m['rmse']:>8.2f}")

    mean_mape = float(np.mean([m["mape"] for m in fold_metrics]))
    r2s = [m["r2"] for m in fold_metrics if not np.isnan(m["r2"])]
    mean_r2 = float(np.mean(r2s)) if r2s else float("nan")
    mean_rmse = float(np.mean([m["rmse"] for m in fold_metrics]))
    print(f"\nMEAN  MAPE={mean_mape:.2f}%   R2={mean_r2:.3f}   RMSE={mean_rmse:.2f} kg")
    print(f"Thesis targets: MAPE < 10%  ({'OK' if mean_mape < 10 else 'NOT MET'}),  "
          f"R2 > 0.85  ({'OK' if mean_r2 > 0.85 else 'NOT MET'})")

    # Fit final model on all data and save
    final = build_model(args.model)
    final.fit(X, y)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": final, "features": args.features, "target": args.target}, out)
    print(f"\nSaved model -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
