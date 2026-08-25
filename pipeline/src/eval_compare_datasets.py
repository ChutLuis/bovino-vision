"""Compara honestamente 3 datasets para el modelo de peso, mismo metodo de evaluacion:
  A) fotos_hoy        (1 foto/vaca, marcador en poste = escala mas consistente)
  B) rafagas manana   (varias fotos/vaca desde mascaras anotadas; marcador a dist. variable)
  C) combinado        (A + B, mediana por vaca sobre ambas)

Agregacion: mediana por vaca (+ filtro relativo de outliers intra-vaca, 18% sobre la mediana,
que quita escalas malas SIN asumir un cm absoluto). Evaluacion: leave-one-out por animal.
Modelos: alometrico area->peso (principal) y lineal 6-feat. Reporta MAPE/IC95/R2/RMSE/N.

    python3 src/eval_compare_datasets.py
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.metrics import r2_score

FEATURES = ["body_length_cm","height_cm","chest_depth_cm","lateral_area_cm2","aspect_ratio","fill_ratio"]
DEV = 0.18
RNG = np.random.default_rng(0)


def mape(y,p): return float(np.mean(np.abs((y-p)/y))*100)
def rmse(y,p): return float(np.sqrt(np.mean((y-p)**2)))


def boot_ci(y,p,n=2000):
    v=[mape(y[i],p[i]) for i in (RNG.integers(0,len(y),len(y)) for _ in range(n))]
    return np.percentile(v,[2.5,97.5])


def median_per_cow(df):
    """1 fila por vaca: filtra fotos cuya longitud se desvia >DEV de la mediana intra-vaca, luego mediana."""
    out=[]
    for cid,g in df.groupby("cow_id"):
        med=g["body_length_cm"].median()
        gg=g[(g["body_length_cm"]-med).abs() <= DEV*med] if len(g)>1 else g
        if gg.empty: gg=g
        row={"cow_id":cid,"weight_kg":gg["weight_kg"].iloc[0],"n":len(gg)}
        for f in FEATURES: row[f]=gg[f].median()
        out.append(row)
    return pd.DataFrame(out)


def loo_lin(X,y):
    n=len(y); pr=np.zeros(n)
    for i in range(n):
        tr=np.arange(n)!=i
        m=make_pipeline(StandardScaler(),LinearRegression()).fit(X[tr],y[tr])
        pr[i]=m.predict(X[i:i+1])[0]
    return pr


def loo_loglog(area,y):
    n=len(y); pr=np.zeros(n)
    for i in range(n):
        tr=np.arange(n)!=i
        b,a=np.polyfit(np.log(area[tr]),np.log(y[tr]),1)
        pr[i]=np.exp(a+b*np.log(area[i]))
    return pr


def evaluate(name,df):
    d=median_per_cow(df).dropna(subset=FEATURES+["weight_kg"])
    y=d["weight_kg"].to_numpy(float); area=d["lateral_area_cm2"].to_numpy(float)
    X=d[FEATURES].to_numpy(float)
    res={}
    for mdl,pred in [("area log-log",loo_loglog(area,y)),("lineal 6f",loo_lin(X,y))]:
        lo,hi=boot_ci(y,pred)
        res[mdl]=(mape(y,pred),lo,hi,r2_score(y,pred),rmse(y,pred))
    print(f"\n### {name}  (N={len(d)} vacas, longitud mediana {np.median(d.body_length_cm):.0f}cm)")
    print(f"{'modelo':14} {'MAPE%':>7} {'IC95':>14} {'R2':>7} {'RMSE':>7}")
    for mdl,(mp,lo,hi,r2,rm) in res.items():
        ok="OK" if mp<10 else "  "
        print(f"{mdl:14} {mp:>6.2f}{ok} [{lo:>4.1f},{hi:>4.1f}] {r2:>6.2f} {rm:>6.1f}")
    return d


fh=pd.read_csv("data/field/features_fotos_hoy.csv").dropna(subset=FEATURES+["weight_kg"])[["cow_id","weight_kg"]+FEATURES]
gr=pd.read_csv("data/field/features_grouped.csv").dropna(subset=FEATURES+["weight_kg"])[["cow_id","weight_kg"]+FEATURES]
print(f"fotos_hoy: {len(fh)} fotos / {fh.cow_id.nunique()} vacas | rafagas: {len(gr)} fotos / {gr.cow_id.nunique()} vacas")
print(f"rafagas longitud cruda: min {gr.body_length_cm.min():.0f} max {gr.body_length_cm.max():.0f} mediana {gr.body_length_cm.median():.0f} cm")

evaluate("A) fotos_hoy", fh)
evaluate("B) rafagas manana", gr)
evaluate("C) combinado (fotos_hoy + rafagas)", pd.concat([fh,gr], ignore_index=True))
