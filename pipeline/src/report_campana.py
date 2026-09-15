"""Informe de la campaña de calibración (La Primavera, 12 sep 2026): decodificación, repetibilidad y robustez a la distancia.

Lee los CSV de `data/field/campana_20260912/` (rasgos por fotografía, bitácora por animal y fotos por vaca) y escribe
en `informes/campana_20260912/`:

  resumen.md                    campaña, decodificación, distribución por nivel de distancia, morfometría implícita,
                                selección a 3.0 m, tabla decisión → evidencia y repetibilidad (ICC(1) del log-área)
  repetibilidad.csv / .png      por animal: n, medianas y CV intra del área cruda y corregida (todas / seleccionadas)
  robustez_distancia.csv        por nivel: cociente de área respecto a 3.0 m (cruda y corregida)
  robustez_distancia_delta.csv  Δ ∈ {0.0, …, 1.0} m: pendiente %/m con efectos fijos por animal y CV intra mediana
  robustez_distancia.png / .md  área relativa vs distancia; curva Δ → pendiente; método, tablas y lectura
  mosaico_seleccion_3m.jpg      una fotografía por animal (la seleccionada más cercana a 3.0 m); solo con --fotos

Conteos, percentiles, ICC, CV y pendientes salen de los CSV; el texto fija solo el protocolo de la campaña.

    python3 src/report_campana.py --fotos ~/Documents/Thesis_photos_12_09
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from PIL import Image, ImageDraw, ImageFont, ImageOps  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "field" / "campana_20260912"
OUT_DEFAULT = ROOT.parent / "informes" / "campana_20260912"

DELTA_PARALAJE_M = 0.50
MARKER_CM = 15.0
NIVELES = (2.5, 3.0, 3.5)
NIVEL_REF = 3.0
N_SELECCION = 5
DELTAS = tuple(round(0.1 * i, 1) for i in range(11))
MOSAICO_MAX_BYTES = 2_000_000

# Hechos del protocolo que no están en los CSV: manifiesto de fotografías y separación por animal.
CAMPANA = {"fecha": "12 de septiembre de 2026", "finca": "La Primavera", "raza": "Jersey",
           "n_fotos": 1226, "n_tabla": 27, "n_descartadas": 1}
TELEFONOS = {"xiaomi_15_ultra": ("Xiaomi 15 Ultra", "4096×3072", 23), "galaxy_a25": ("Galaxy A25", "4080×3060", 27)}
ESTADOS = ("ok", "sin_marcador", "sin_vaca", "silueta_cortada")

AZUL, NARANJA, GRIS, TINTA, NEGRO = "#2a78d6", "#eb6834", "#a3a29d", "#52514e", "#0b0b0b"
NUMERICAS = ["marker_px", "px_per_cm", "distancia_m", "nivel_distancia", "cow_conf", "area_px", "lateral_area_cm2",
             "lateral_area_cm2_corr", "body_length_cm", "height_cm", "chest_depth_cm", "aspect_ratio", "fill_ratio",
             "marcador_en_caja", "seleccionada_3m"]


# ----------------------------------------------------------------------------------------------------------------- datos
def leer_features(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"foto": str, "nombre": str, "arete": str, "telefono": str, "estado": str})
    for c in NUMERICAS:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["fila"] = df["fila"].astype(int)
    df["seleccionada_3m"] = df["seleccionada_3m"].fillna(0).astype(int)
    return df


def leer_bitacora(path: Path, features: pd.DataFrame) -> pd.DataFrame:
    if path.exists():
        b = pd.read_csv(path, dtype=str, keep_default_na=False)
        b["fila"] = b["fila"].astype(int)
        return b
    print(f"aviso: sin bitácora en {path}; nombres y teléfonos tomados de los rasgos", file=sys.stderr)
    return features.groupby("fila").agg(nombre=("nombre", "first"), telefono=("telefono", "first")).reset_index()


def leer_fotos_por_vaca(path: Path, features: pd.DataFrame) -> pd.DataFrame:
    if path.exists():
        f = pd.read_csv(path, dtype=str)
        f["fila"] = f["fila"].astype(int)
        return f
    print(f"aviso: sin fotos por vaca en {path}; conteos tomados de los rasgos", file=sys.stderr)
    return features[["foto", "fila", "nombre", "telefono"]].copy()


# ------------------------------------------------------------------------------------------------------------ estadística
def cv_pct(x) -> float:
    """Coeficiente de variación muestral (sd con ddof = 1 sobre la media), en %."""
    v = np.asarray(x, float)
    v = v[np.isfinite(v)]
    if len(v) < 2 or v.mean() == 0:
        return float("nan")
    return float(100.0 * v.std(ddof=1) / v.mean())


def icc1(grupos, valores) -> float:
    """ICC(1) de una vía (Shrout–Fleiss, caso 1) para grupos desbalanceados.

    MSB = Σ n_i·(ȳ_i − ȳ)² / (k − 1); MSW = Σ_i Σ_j (y_ij − ȳ_i)² / (N − k);
    n0 = (N − Σ n_i² / N) / (k − 1), tamaño medio de grupo corregido (Searle);
    ICC(1) = (MSB − MSW) / (MSB + (n0 − 1)·MSW). Con varianza intra nula vale 1.0.
    """
    df = pd.DataFrame({"g": np.asarray(grupos), "y": np.asarray(valores, float)}).dropna()
    k, n = df["g"].nunique(), len(df)
    if k < 2 or n <= k:
        return float("nan")
    med = df.groupby("g")["y"].agg(["mean", "size"])
    msb = float((med["size"] * (med["mean"] - df["y"].mean()) ** 2).sum() / (k - 1))
    msw = float(((df["y"] - df["g"].map(med["mean"])) ** 2).sum() / (n - k))
    n0 = (n - float((med["size"] ** 2).sum()) / n) / (k - 1)
    den = msb + (n0 - 1.0) * msw
    return float((msb - msw) / den) if den > 0 else float("nan")


def pendiente_efectos_fijos(grupos, d, y) -> tuple[float, float]:
    """Pendiente común de y sobre d con efectos fijos por grupo (ambas variables centradas dentro de cada grupo).

    Devuelve (pendiente, error estándar); el error usa N − k − 1 grados de libertad.
    """
    df = pd.DataFrame({"g": np.asarray(grupos), "d": np.asarray(d, float), "y": np.asarray(y, float)}).dropna()
    k = df["g"].nunique()
    dt = df["d"] - df.groupby("g")["d"].transform("mean")
    yt = df["y"] - df.groupby("g")["y"].transform("mean")
    sxx = float((dt ** 2).sum())
    gl = len(df) - k - 1
    if sxx <= 0 or gl <= 0:
        return float("nan"), float("nan")
    b = float((dt * yt).sum() / sxx)
    res = yt - b * dt
    return b, math.sqrt(float((res ** 2).sum()) / gl / sxx)


def area_corregida(area, d, delta: float) -> np.ndarray:
    """Corrección de paralaje del marcador: A·((d + Δ)/d)²."""
    a, dd = np.asarray(area, float), np.asarray(d, float)
    return a * ((dd + delta) / dd) ** 2


def curva_delta(ok: pd.DataFrame, deltas=DELTAS) -> pd.DataFrame:
    """Para cada Δ: pendiente intra-animal de log(A_corr(Δ)) sobre d (%/m, con su error estándar) y CV intra mediana."""
    filas = []
    for delta in deltas:
        ac = pd.Series(area_corregida(ok["lateral_area_cm2"], ok["distancia_m"], delta), index=ok.index)
        b, ee = pendiente_efectos_fijos(ok["fila"], ok["distancia_m"], np.log(ac))
        cv = float(ac.groupby(ok["fila"]).apply(cv_pct).median())
        filas.append({"delta_m": delta, "pendiente_pct_por_m": 100.0 * b, "ee_pct_por_m": 100.0 * ee,
                      "cv_intra_mediana_pct": cv})
    return pd.DataFrame(filas)


def delta_cruce_cero(curva: pd.DataFrame) -> float:
    """Δ* donde la pendiente cruza cero: interpolación lineal entre dos puntos consecutivos de la malla; NaN si no cruza."""
    x = curva["delta_m"].to_numpy(float)
    p = curva["pendiente_pct_por_m"].to_numpy(float)
    for i in range(len(x) - 1):
        if np.isfinite(p[i]) and np.isfinite(p[i + 1]) and p[i] * p[i + 1] <= 0 and p[i] != p[i + 1]:
            return float(x[i] - p[i] * (x[i + 1] - x[i]) / (p[i + 1] - p[i]))
    return float("nan")


# ---------------------------------------------------------------------------------------------------------------- tablas
def tabla_repetibilidad(ok: pd.DataFrame, nombres: dict[int, str]) -> pd.DataFrame:
    filas = []
    for fila, g in ok.groupby("fila"):
        s = g[g["seleccionada_3m"] == 1]
        filas.append({"fila": int(fila), "nombre": nombres.get(int(fila), g["nombre"].iloc[0]),
                      "n_ok": len(g), "n_sel": len(s),
                      "mediana_area": round(float(g["lateral_area_cm2"].median()), 1),
                      "mediana_area_corr": round(float(g["area_corr"].median()), 1),
                      "cv_area_pct": round(cv_pct(g["lateral_area_cm2"]), 2),
                      "cv_area_corr_pct": round(cv_pct(g["area_corr"]), 2),
                      "cv_area_sel_pct": round(cv_pct(s["lateral_area_cm2"]), 2),
                      "cv_area_corr_sel_pct": round(cv_pct(s["area_corr"]), 2)})
    return pd.DataFrame(filas)


def referencia_3m(ok: pd.DataFrame) -> pd.DataFrame:
    """Mediana por animal del área cruda y corregida en el nivel de referencia (3.0 m)."""
    return ok[ok["nivel_distancia"] == NIVEL_REF].groupby("fila")[["lateral_area_cm2", "area_corr"]].median()


def tabla_robustez(ok: pd.DataFrame) -> pd.DataFrame:
    """Por nivel: n fotografías ok, n animales con fotos en el nivel y a 3.0 m, y mediana entre animales del cociente
    (mediana del animal en el nivel) / (mediana del animal a 3.0 m), para el área cruda y la corregida."""
    ref = referencia_3m(ok)
    filas = []
    for nivel in NIVELES:
        g = ok[ok["nivel_distancia"] == nivel]
        med = g.groupby("fila")[["lateral_area_cm2", "area_corr"]].median()
        comunes = med.index.intersection(ref.index)
        r = med.loc[comunes] / ref.loc[comunes]
        filas.append({"nivel": f"{nivel:.1f}", "n_fotos": len(g), "n_vacas": len(comunes),
                      "cociente_area": round(float(r["lateral_area_cm2"].median()), 4) if len(comunes) else float("nan"),
                      "cociente_area_corr": round(float(r["area_corr"].median()), 4) if len(comunes) else float("nan")})
    return pd.DataFrame(filas)


def area_relativa(ok: pd.DataFrame) -> pd.DataFrame:
    """Por fotografía: área / mediana del mismo animal a 3.0 m (cruda y corregida); solo animales con referencia."""
    ref = referencia_3m(ok)
    r = ok[ok["fila"].isin(ref.index)].copy()
    r["rel_area"] = r["lateral_area_cm2"] / r["fila"].map(ref["lateral_area_cm2"])
    r["rel_area_corr"] = r["area_corr"] / r["fila"].map(ref["area_corr"])
    return r


def percentiles(s: pd.Series, qs=(2.5, 5, 50, 95, 97.5)) -> dict[float, float]:
    v = s.dropna().to_numpy(float)
    return {q: float(np.percentile(v, q)) if len(v) else float("nan") for q in qs}


# --------------------------------------------------------------------------------------------------------------- figuras
def _estilo(ax) -> None:
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_color(GRIS)
    ax.tick_params(colors=TINTA, labelsize=8)
    ax.yaxis.grid(True, color="#e6e5e1", lw=0.8)
    ax.set_axisbelow(True)
    ax.xaxis.label.set_color(TINTA)
    ax.yaxis.label.set_color(TINTA)


def figura_repetibilidad(ok: pd.DataFrame, rep: pd.DataFrame, out: Path) -> None:
    orden = rep.sort_values(["mediana_area_corr", "fila"])["fila"].tolist()
    pos = {f: i for i, f in enumerate(orden)}
    rng = np.random.default_rng(0)
    x = ok["fila"].map(pos).to_numpy(float) + rng.uniform(-0.28, 0.28, len(ok))
    sel = (ok["seleccionada_3m"] == 1).to_numpy()
    fig, ax = plt.subplots(figsize=(12, 4.8))
    ax.scatter(x[~sel], ok["area_corr"].to_numpy()[~sel], s=9, c=GRIS, alpha=0.55, linewidths=0,
               label=f"fotografías ok no seleccionadas (n = {int((~sel).sum())})")
    ax.scatter(x[sel], ok["area_corr"].to_numpy()[sel], s=16, c=AZUL, alpha=0.9, linewidths=0,
               label=f"seleccionadas a 3.0 m (n = {int(sel.sum())})")
    med = rep.set_index("fila").loc[orden, "mediana_area_corr"]
    ax.scatter(range(len(orden)), med, marker="_", s=240, c=NEGRO, linewidths=1.6, label="mediana por animal")
    ax.set_xticks(range(len(orden)))
    ax.set_xticklabels([str(f) for f in orden], fontsize=7)
    ax.set_xlabel("Animal (fila de la bitácora), ordenado por la mediana del área corregida")
    ax.set_ylabel("Área lateral corregida (cm²)")
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    _estilo(ax)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def figura_robustez(rel: pd.DataFrame, rob: pd.DataFrame, curva: pd.DataFrame, delta: float, delta_star: float,
                    out: Path) -> None:
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 4.8))
    niveles = [float(n) for n in rob["nivel"]]
    a1.scatter(rel["distancia_m"], rel["rel_area"], s=8, c=AZUL, alpha=0.28, linewidths=0)
    a1.scatter(rel["distancia_m"], rel["rel_area_corr"], s=8, c=NARANJA, alpha=0.28, linewidths=0)
    a1.plot(niveles, rob["cociente_area"], "o-", c=AZUL, ms=7, mec="white", mew=1.2, lw=2, label="cruda")
    a1.plot(niveles, rob["cociente_area_corr"], "s-", c=NARANJA, ms=7, mec="white", mew=1.2, lw=2,
            label=f"corregida, Δ = {delta:.2f} m")
    a1.axhline(1.0, c=GRIS, lw=1, ls="--")
    for serie, dy in ((rob["cociente_area"], 6), (rob["cociente_area_corr"], -12)):
        for xv, yv in zip(niveles, serie):
            if np.isfinite(yv) and xv != NIVEL_REF:  # a 3.0 m el cociente es 1 por construcción
                a1.annotate(f"{yv:.3f}", (xv, yv), xytext=(0, dy), textcoords="offset points", ha="center",
                            fontsize=7, color=TINTA)
    lo = float(np.nanpercentile(pd.concat([rel["rel_area"], rel["rel_area_corr"]]), 0.5))
    hi = float(np.nanpercentile(pd.concat([rel["rel_area"], rel["rel_area_corr"]]), 99.5))
    a1.set_ylim(min(lo, 0.85) - 0.03, max(hi, 1.15) + 0.03)
    a1.set_xlabel("Distancia estimada por el marcador (m)")
    a1.set_ylabel("Área relativa a la mediana del animal a 3.0 m")
    a1.set_title("Área por fotografía y mediana por nivel", fontsize=10, color=NEGRO)
    a1.legend(frameon=False, fontsize=8, title="área lateral", title_fontsize=8, loc="upper left")
    _estilo(a1)

    a2.plot(curva["delta_m"], curva["pendiente_pct_por_m"], "o-", c=AZUL, ms=6, mec="white", mew=1.0, lw=2)
    a2.axhline(0.0, c=GRIS, lw=1, ls="--")
    p_delta = float(np.interp(delta, curva["delta_m"], curva["pendiente_pct_por_m"]))
    a2.axvline(delta, c=NARANJA, lw=1.2, ls=":")
    a2.annotate(f"Δ = {delta:.2f} m: {p_delta:+.1f} %/m", (delta, p_delta), xytext=(8, 10), textcoords="offset points",
                fontsize=8, color=TINTA)
    if np.isfinite(delta_star):
        a2.plot([delta_star], [0.0], "D", c=NEGRO, ms=6)
        a2.annotate(f"Δ* = {delta_star:.2f} m", (delta_star, 0.0), xytext=(-8, -16), textcoords="offset points",
                    ha="right", fontsize=8, color=TINTA)
    a2.set_xlabel("Δ (m)")
    a2.set_ylabel("Pendiente intra-animal de log(área corregida) (%/m)")
    a2.set_title("Pendiente residual según Δ", fontsize=10, color=NEGRO)
    _estilo(a2)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


# --------------------------------------------------------------------------------------------------------------- mosaico
def _fuente(tam: int):
    """DejaVu Sans (la trae matplotlib; cubre ñ y tildes); si no, la fuente por defecto de Pillow."""
    try:
        from matplotlib import font_manager
        return ImageFont.truetype(font_manager.findfont("DejaVu Sans"), tam)
    except Exception:
        try:
            return ImageFont.load_default(size=tam)
        except TypeError:  # Pillow < 10.1
            return ImageFont.load_default()


def _buscar_foto(fotos: Path, nombre: str) -> Path | None:
    p = fotos / nombre
    if p.exists():
        return p
    return next(fotos.rglob(nombre), None)


def _miniatura(path: Path | None, tam: tuple[int, int]) -> Image.Image:
    if path is None:
        im = Image.new("RGB", tam, (215, 214, 210))
        ImageDraw.Draw(im).text((8, 8), "sin archivo", fill=NEGRO, font=_fuente(14))
        return im
    im = Image.open(path)
    im.draft("RGB", (tam[0] * 2, tam[1] * 2))
    im = ImageOps.exif_transpose(im).convert("RGB")
    return ImageOps.fit(im, tam, Image.Resampling.LANCZOS)


def fotos_mosaico(feat: pd.DataFrame) -> pd.DataFrame:
    """Una fotografía por animal: la seleccionada más cercana a 3.0 m (si no hay seleccionadas, la ok más cercana)."""
    ok = feat[feat["estado"] == "ok"]
    elegidas = []
    for _, g in ok.groupby("fila"):
        s = g[g["seleccionada_3m"] == 1] if (g["seleccionada_3m"] == 1).any() else g
        s = s.assign(_d=(s["distancia_m"] - NIVEL_REF).abs()).sort_values(["_d", "foto"])
        elegidas.append(s.iloc[0].drop("_d"))
    return pd.DataFrame(elegidas).reset_index(drop=True)


def mosaico(feat: pd.DataFrame, nombres: dict[int, str], fotos: Path, out: Path, tam=(320, 240), calidad=80,
            max_bytes=MOSAICO_MAX_BYTES) -> tuple[int, tuple[int, int], pd.DataFrame]:
    """Miniaturas de la fotografía seleccionada más cercana a 3.0 m por animal, 8 columnas, JPEG calidad `calidad`.
    Si el archivo supera `max_bytes`, reduce el tamaño de miniatura y repite. Devuelve (bytes, (columnas, filas), fotos)."""
    elegidas = fotos_mosaico(feat)
    n = len(elegidas)
    cols = min(8, n)
    filas = math.ceil(n / cols)
    while True:
        tw, th = tam
        etiqueta = max(18, th // 9)
        lienzo = Image.new("RGB", (cols * tw, filas * (th + etiqueta)), "white")
        dibujo = ImageDraw.Draw(lienzo)
        fuente = _fuente(max(11, etiqueta - 8))
        for i, r in elegidas.iterrows():
            x, y = (i % cols) * tw, (i // cols) * (th + etiqueta)
            lienzo.paste(_miniatura(_buscar_foto(fotos, str(r["foto"])), (tw, th)), (x, y))
            texto = f"{int(r['fila'])} · {nombres.get(int(r['fila']), r['nombre'])} · {float(r['distancia_m']):.2f} m"
            dibujo.text((x + 6, y + th + 3), texto, fill=NEGRO, font=fuente)
        lienzo.save(out, "JPEG", quality=calidad, optimize=True)
        tamano = out.stat().st_size
        if tamano <= max_bytes or tw <= 160:
            return tamano, (cols, filas), elegidas
        tam = (int(tw * 0.85), int(th * 0.85))


# ----------------------------------------------------------------------------------------------------------------- texto
def _f(x: float, nd: int = 2) -> str:
    return "—" if x is None or not np.isfinite(x) else f"{x:.{nd}f}"


def _pm(x: float, nd: int = 1) -> str:
    return "—" if not np.isfinite(x) else f"{x:+.{nd}f}"


def texto_robustez(rob: pd.DataFrame, curva: pd.DataFrame, delta: float, delta_star: float, n_ok: int,
                   n_vacas: int) -> str:
    c0 = curva.iloc[0]
    cd = curva.iloc[int(np.argmin(np.abs(curva["delta_m"] - delta)))]
    md = ["# Robustez a la distancia y corrección de paralaje", "",
          f"Fotografías con `estado == ok`: {n_ok} de {n_vacas} animales, en tres niveles nominales (2.5, 3.0 y 3.5 m). "
          "Distancia por fotografía `d = f_px·0.15/marker_px`, con `f_px = W·f35/36` (EXIF); nivel = el más cercano "
          "(cortes 2.75 y 3.25 m).", "",
          "## Método", "",
          "- **Área relativa** por fotografía: área / mediana del mismo animal en el nivel 3.0 m. **Cociente por nivel**: "
          "mediana entre animales de (mediana del animal en el nivel) / (mediana del animal a 3.0 m); solo animales con "
          "fotografías en ambos niveles.",
          "- **Pendiente** (%/m): regresión de `log(A·((d+Δ)/d)²)` sobre `d` con efectos fijos por animal (ambas variables "
          "centradas dentro de cada animal, pendiente común), ×100. Error estándar con N − k − 1 grados de libertad.",
          "- **CV intra mediana**: mediana entre animales del coeficiente de variación de `A_corr(Δ)` sobre todas sus "
          "fotografías `ok`.",
          "- **Δ\\***: valor de Δ donde la pendiente cruza cero, por interpolación lineal entre dos puntos consecutivos de "
          "la malla Δ ∈ {0.0, 0.1, …, 1.0} m.", "",
          "## Cociente de área por nivel (`robustez_distancia.csv`)", "",
          "| nivel (m) | fotografías ok | animales | cociente área cruda | cociente área corregida |", "|---|---|---|---|---|"]
    for _, r in rob.iterrows():
        md.append(f"| {r['nivel']} | {int(r['n_fotos'])} | {int(r['n_vacas'])} | {_f(r['cociente_area'], 4)} | "
                  f"{_f(r['cociente_area_corr'], 4)} |")
    md += ["", "## Pendiente según Δ (`robustez_distancia_delta.csv`)", "",
           "| Δ (m) | pendiente (%/m) | error estándar (%/m) | CV intra mediana (%) |", "|---|---|---|---|"]
    for _, r in curva.iterrows():
        marca = " ←" if abs(r["delta_m"] - delta) < 1e-9 else ""
        md.append(f"| {r['delta_m']:.1f}{marca} | {_pm(r['pendiente_pct_por_m'])} | {_f(r['ee_pct_por_m'])} | "
                  f"{_f(r['cv_intra_mediana_pct'])} |")
    md += ["",
           f"Pendiente cruda (Δ = 0): {_pm(c0['pendiente_pct_por_m'])} %/m (e.e. {_f(c0['ee_pct_por_m'])}); "
           f"con Δ = {delta:.2f} m: {_pm(cd['pendiente_pct_por_m'])} %/m (e.e. {_f(cd['ee_pct_por_m'])}). "
           f"CV intra mediana: {_f(c0['cv_intra_mediana_pct'], 1)} % → {_f(cd['cv_intra_mediana_pct'], 1)} %. "
           + (f"Δ\\* (cruce por cero) = {delta_star:.2f} m." if np.isfinite(delta_star)
              else "La pendiente no cruza cero en la malla explorada."), "",
           "## Lectura", "",
           f"1. **Tendencia cruda.** El área lateral crece {_pm(c0['pendiente_pct_por_m'])} %/m con la distancia dentro "
           "de cada animal. El marcador se sostiene junto al costado, delante del plano de la silueta: la escala px/cm se "
           "sobreestima más cuanto más cerca está la cámara y el área en cm² se subestima más de cerca. Parte del efecto "
           "puede venir de la máscara a menor escala (el segmentador ve la silueta con menos píxeles a 3.5 m), por lo que "
           "la corrección se presenta como empírica.",
           f"2. **Corrección `A_corr = A·((d+Δ)/d)²` con Δ = {delta:.2f} m.** Fórmula única y continua en `d`, no por "
           "tramos: no introduce saltos en los cortes 2.75 y 3.25 m y se aplica igual a cualquier distancia dentro del "
           f"rango. Δ se calibró por invarianza intra-animal, sin pesos: la pendiente residual pasa a "
           f"{_pm(cd['pendiente_pct_por_m'])} %/m"
           + (f" (Δ\\* = {delta_star:.2f} m)" if np.isfinite(delta_star) else "")
           + f" y el CV intra mediana baja de {_f(c0['cv_intra_mediana_pct'], 1)} % a "
           f"{_f(cd['cv_intra_mediana_pct'], 1)} %.",
           "3. **Cruda o corregida.** Se conservan las dos columnas (`lateral_area_cm2`, `lateral_area_cm2_corr`); la "
           "invarianza a la distancia no decide por sí sola cuál predice mejor el peso. La decisión la toma la validación "
           "leave-one-out con los pesos de referencia (`eval_weight_campana.py`: MAPE LOO por área).",
           "4. **Uso de las fotografías.** El modelo principal usa por animal las 5 fotografías `ok` más cercanas a 3.0 m; "
           "todas las fotografías `ok` sirven para esta robustez a la distancia y para el pliegue por distancia del "
           "evaluador.", ""]
    return "\n".join(md)


def texto_resumen(ctx: dict) -> str:
    c, tel = CAMPANA, TELEFONOS
    f, fpv, b = ctx["features"], ctx["fotos_por_vaca"], ctx["bitacora"]
    ok = ctx["ok"]
    n_med, n_ok = len(f), len(ok)
    n_tel = fpv["telefono"].value_counts()
    n_a25 = int(n_tel.get("galaxy_a25", 0))
    n_xiaomi = int(n_tel.get("xiaomi_15_ultra", 0))
    n_xiaomi_total = c["n_fotos"] - n_a25
    por_animal = fpv.groupby("fila").size()
    a25_filas = b[b["telefono"] == "galaxy_a25"]
    a25_txt = ", ".join(f"{int(r['fila'])} ({r['nombre']})" for _, r in a25_filas.iterrows()) or "ninguno"
    est = f["estado"].value_counts()
    n_marc, n_vaca = int(f["marker_px"].notna().sum()), int(f["cow_conf"].notna().sum())
    con_caja = ok["marcador_en_caja"].notna()
    sel = ok[ok["seleccionada_3m"] == 1]
    sel_caja = sel["marcador_en_caja"].notna()
    rep, rob, curva = ctx["rep"], ctx["rob"], ctx["curva"]
    icc = ctx["icc"]
    delta, delta_star = ctx["delta"], ctx["delta_star"]
    c0 = curva.iloc[0]
    cd = curva.iloc[int(np.argmin(np.abs(curva["delta_m"] - delta)))]
    con5 = rep[rep["n_sel"] >= N_SELECCION]
    menos = rep[rep["n_sel"] < N_SELECCION]
    pa, pl = ctx["p_altura"], ctx["p_longitud"]
    par, pac = ctx["p_area"], ctx["p_area_corr"]
    sel_niv = sel["nivel_distancia"].value_counts()

    md = [f"# Campaña de calibración — {c['finca']}, {c['fecha']}", "",
          f"{c['finca']}; {len(b)} animales {c['raza']}; unas {int(round(por_animal.median()))} fotografías por animal "
          f"(mín {int(por_animal.min())}, máx {int(por_animal.max())}) a 2.5, 3.0 y 3.5 m, con el marcador ArUco id 0 de "
          f"{MARKER_CM:.0f} cm sostenido junto al costado del animal. {c['n_fotos']} fotografías: {n_xiaomi_total} "
          f"{tel['xiaomi_15_ultra'][0]} ({tel['xiaomi_15_ultra'][1]}, equiv. {tel['xiaomi_15_ultra'][2]} mm) y {n_a25} "
          f"{tel['galaxy_a25'][0]} ({tel['galaxy_a25'][1]}, equiv. {tel['galaxy_a25'][2]} mm); {c['n_tabla']} de la tabla "
          f"de registro entre animales y {c['n_descartadas']} suelta descartada, así que quedan {n_med} medidas "
          f"({tel['xiaomi_15_ultra'][0]} {n_xiaomi} / {tel['galaxy_a25'][0]} {n_a25}). Animales fotografiados solo con el "
          f"{tel['galaxy_a25'][0]}: {a25_txt}. Los pesos de referencia los conserva la finca; la categoría no se registró.",
          "",
          "Distancia por fotografía `d = f_px·0.15/marker_px`, con `f_px = W·f35/36` (EXIF `FocalLengthIn35mmFilm`); nivel "
          "de distancia = el más cercano de {2.5, 3.0, 3.5} m (cortes 2.75 y 3.25). Corrección de paralaje del marcador "
          f"`A_corr = A·((d+Δ)/d)²`, Δ = {delta:.2f} m; solo se corrige el área. Escala: 15 cm / lado medio del marcador.",
          ""]
    if ctx["avisos"]:
        md += [f"Aviso: {a}" for a in ctx["avisos"]] + [""]
    md += ["## Decodificación", "",
           "| paso | fotografías | % de las medidas |", "|---|---|---|",
           f"| medidas (fotos por vaca) | {n_med} | 100.0 |",
           f"| marcador ArUco id 0 detectado | {n_marc} | {100 * n_marc / n_med:.1f} |",
           f"| vaca segmentada | {n_vaca} | {100 * n_vaca / n_med:.1f} |",
           f"| `ok` (marcador, vaca y silueta completa) | {n_ok} | {100 * n_ok / n_med:.1f} |", "",
           "Estados: " + ", ".join(f"`{e}` {int(est.get(e, 0))}" for e in ESTADOS) + ". Por teléfono: "
           + "; ".join(f"{tel.get(t, (t,))[0]} {int((f['telefono'] == t).sum())} medidas, "
                       f"{int(((f['telefono'] == t) & (f['estado'] == 'ok')).sum())} `ok`" for t in n_tel.index) + ".",
           f"Centro del marcador dentro de la caja de la vaca: {int(ok['marcador_en_caja'].sum())}/{int(con_caja.sum())} "
           f"de las `ok`; {int(sel['marcador_en_caja'].sum())}/{int(sel_caja.sum())} de las seleccionadas a 3.0 m.", "",
           "## Distribución por nivel de distancia", "",
           "| nivel (m) | fotografías | `ok` | animales con `ok` | d de las `ok`: mediana (mín–máx) |", "|---|---|---|---|---|"]
    for nivel in NIVELES:
        g = f[f["nivel_distancia"] == nivel]
        go = ok[ok["nivel_distancia"] == nivel]
        d = go["distancia_m"]
        md.append(f"| {nivel:.1f} | {len(g)} | {len(go)} | {go['fila'].nunique()} | "
                  f"{_f(d.median())} ({_f(d.min())}–{_f(d.max())}) |")
    md.append(f"| sin marcador | {int(f['nivel_distancia'].isna().sum())} | — | — | — |")
    md += ["", f"## Morfometría implícita (`estado == ok`, n = {n_ok})", "",
           "| medida | p2.5 | p5 | p50 | p95 | p97.5 |", "|---|---|---|---|---|---|",
           f"| altura (cm) | {_f(pa[2.5], 1)} | {_f(pa[5], 1)} | {_f(pa[50], 1)} | {_f(pa[95], 1)} | {_f(pa[97.5], 1)} |",
           f"| longitud del cuerpo (cm) | {_f(pl[2.5], 1)} | {_f(pl[5], 1)} | {_f(pl[50], 1)} | {_f(pl[95], 1)} | "
           f"{_f(pl[97.5], 1)} |",
           f"| área lateral cruda (cm²) | {_f(par[2.5], 0)} | {_f(par[5], 0)} | {_f(par[50], 0)} | {_f(par[95], 0)} | "
           f"{_f(par[97.5], 0)} |",
           f"| área lateral corregida (cm²) | {_f(pac[2.5], 0)} | {_f(pac[5], 0)} | {_f(pac[50], 0)} | {_f(pac[95], 0)} | "
           f"{_f(pac[97.5], 0)} |", "",
           f"Rango de plausibilidad de la longitud recalibrado con la campaña: [{_f(pl[2.5], 0)}, {_f(pl[97.5], 0)}] cm "
           f"(p2.5–p97.5 sobre las {n_ok} medidas `ok`). El rango del piloto (`PLAUS_LEN` 110–190 cm en "
           "`measure_fotos_hoy.py`, con el marcador en el poste) no se aplica a estas medidas.", "",
           "## Selección a 3.0 m", "",
           f"Por animal, las {N_SELECCION} fotografías `ok` con menor |d − 3.0| (desempate por nombre de archivo). "
           f"Animales con {N_SELECCION} seleccionadas: {len(con5)}/{len(rep)}; con menos: {len(menos)}"
           + (" (" + ", ".join(f"{int(r['fila'])} {r['nombre']}: {int(r['n_sel'])}" for _, r in menos.iterrows()) + ")"
              if len(menos) else "") + ". "
           f"Distancia de las {len(sel)} seleccionadas: mediana {_f(sel['distancia_m'].median())} m "
           f"({_f(sel['distancia_m'].min())}–{_f(sel['distancia_m'].max())}); por nivel: "
           + ", ".join(f"{float(n):.1f} m → {int(sel_niv[n])}" for n in sorted(sel_niv.index)) + ".", "",
           "## Decisión → evidencia", "",
           "| decisión | evidencia |", "|---|---|",
           f"| Corrección de paralaje `A_corr = A·((d+Δ)/d)²` con Δ = {delta:.2f} m, fórmula única y continua (no por "
           f"tramos) | Pendiente intra-animal de log(área) sobre d: {_pm(c0['pendiente_pct_por_m'])} %/m cruda → "
           f"{_pm(cd['pendiente_pct_por_m'])} %/m con Δ = {delta:.2f}"
           + (f" (cruce por cero en Δ\\* = {delta_star:.2f} m)" if np.isfinite(delta_star) else "")
           + f"; CV intra mediana {_f(c0['cv_intra_mediana_pct'], 1)} % → {_f(cd['cv_intra_mediana_pct'], 1)} %; cocientes "
           f"por nivel 2.5/3.5 m: cruda {_f(rob.iloc[0]['cociente_area'], 3)}/{_f(rob.iloc[2]['cociente_area'], 3)}, "
           f"corregida {_f(rob.iloc[0]['cociente_area_corr'], 3)}/{_f(rob.iloc[2]['cociente_area_corr'], 3)} "
           "(`robustez_distancia.md`, `robustez_distancia_delta.csv`). Corrección empírica: el marcador va delante del "
           "plano de la silueta y parte del efecto puede venir de la máscara a menor escala. |",
           f"| Modelo principal con las {N_SELECCION} fotografías por animal más cercanas a 3.0 m | {len(con5)}/{len(rep)} "
           f"animales con {N_SELECCION}; d mediana {_f(sel['distancia_m'].median())} m; ICC(1) del log-área en las "
           f"seleccionadas {_f(icc['sel_area'], 3)} (cruda) / {_f(icc['sel_corr'], 3)} (corregida) frente a "
           f"{_f(icc['todas_area'], 3)} / {_f(icc['todas_corr'], 3)} con todas; CV intra mediana en las seleccionadas "
           f"{_f(rep['cv_area_sel_pct'].median(), 1)} % / {_f(rep['cv_area_corr_sel_pct'].median(), 1)} % "
           "(`repetibilidad.csv`). |",
           "| Se conservan el área cruda y la corregida | La invarianza a la distancia no decide cuál predice mejor el peso; "
           "la validación leave-one-out con los pesos de referencia (`eval_weight_campana.py`, MAPE LOO) elige la que entra "
           "al modelo y deja la otra como alternativa. |",
           f"| Todas las fotografías `ok` sirven para la robustez a la distancia | {n_ok} medidas `ok` en tres niveles ("
           + "/".join(str(int(r["n_fotos"])) for _, r in rob.iterrows()) + " a "
           + "/".join(r["nivel"] for _, r in rob.iterrows()) + " m), {} animales (`robustez_distancia.csv`). |".format(
               ok["fila"].nunique()),
           "", "## Pesos", "",
           "Los pesos de referencia los conserva la finca; el ajuste y la validación se ejecutan con "
           "`eval_weight_campana.py` sobre la misma bitácora (`bitacora_campana_20260912.csv`: `peso_kg`, o media de "
           "`peso_lb1`/`peso_lb2` × 0.45359237).", "",
           "## Repetibilidad", "",
           "| conjunto | fotografías | animales | ICC(1) log(área) | ICC(1) log(área corregida) | CV intra mediana área (%) | "
           "CV intra mediana área corregida (%) |", "|---|---|---|---|---|---|---|",
           f"| todas las `ok` | {n_ok} | {ok['fila'].nunique()} | {_f(icc['todas_area'], 3)} | {_f(icc['todas_corr'], 3)} | "
           f"{_f(rep['cv_area_pct'].median(), 1)} | {_f(rep['cv_area_corr_pct'].median(), 1)} |",
           f"| seleccionadas a 3.0 m | {len(sel)} | {sel['fila'].nunique()} | {_f(icc['sel_area'], 3)} | "
           f"{_f(icc['sel_corr'], 3)} | {_f(rep['cv_area_sel_pct'].median(), 1)} | "
           f"{_f(rep['cv_area_corr_sel_pct'].median(), 1)} |", "",
           "ICC(1) de una vía para grupos desbalanceados: `(MSB − MSW) / (MSB + (n0 − 1)·MSW)`, con "
           "`n0 = (N − Σn_i²/N)/(k − 1)`. El ICC del log-área coincide con el ICC del log-peso para cualquier modelo "
           "alométrico `log peso = log a + b·log área` (transformación afín). Detalle por animal en `repetibilidad.csv`; "
           "`repetibilidad.png` muestra el área corregida por animal (todas las `ok` en gris, seleccionadas en azul, "
           "mediana en negro).", "",
           "## Archivos", "",
           "- `repetibilidad.csv`, `repetibilidad.png`: por animal, n y CV intra del área cruda y corregida (todas / "
           "seleccionadas).",
           "- `robustez_distancia.csv`, `robustez_distancia_delta.csv`, `robustez_distancia.png`, `robustez_distancia.md`: "
           "cociente por nivel, curva Δ → pendiente y lectura."]
    if ctx.get("mosaico_bytes"):
        cols, filas = ctx["mosaico_grid"]
        md.append(f"- `mosaico_seleccion_3m.jpg`: la fotografía seleccionada más cercana a 3.0 m de cada animal "
                  f"({cols}×{filas} miniaturas, {ctx['mosaico_bytes'] / 1e6:.2f} MB).")
    md += ["", "## Reproducir", "", "```", "cd pipeline",
           ".venv/bin/python src/build_campana_csvs.py            # bitácora y fotos por vaca desde la separación por animal",
           ".venv/bin/python src/measure_campana.py               # rasgos por fotografía; overlays QA fuera del repo",
           ".venv/bin/python src/report_campana.py --fotos ~/Documents/Thesis_photos_12_09",
           ".venv/bin/python src/eval_weight_campana.py           # ajuste y validación con los pesos de la bitácora",
           "```", ""]
    return "\n".join(md)


# ------------------------------------------------------------------------------------------------------------------ main
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--features", default=str(DATA / "features_campana_20260912.csv"))
    ap.add_argument("--bitacora", default=str(DATA / "bitacora_campana_20260912.csv"))
    ap.add_argument("--fotos-por-vaca", default=str(DATA / "fotos_por_vaca.csv"))
    ap.add_argument("--fotos", default=None, help="directorio con las fotografías originales; con él se escribe el mosaico")
    ap.add_argument("--out", default=str(OUT_DEFAULT))
    ap.add_argument("--delta", type=float, default=DELTA_PARALAJE_M,
                    help="Δ (m) de la corrección de paralaje con que se calculó lateral_area_cm2_corr")
    a = ap.parse_args(argv)

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    feat = leer_features(Path(a.features))
    bit = leer_bitacora(Path(a.bitacora), feat)
    fpv = leer_fotos_por_vaca(Path(a.fotos_por_vaca), feat)
    nombres = dict(zip(bit["fila"], bit["nombre"]))
    avisos: list[str] = []

    esperadas = CAMPANA["n_fotos"] - CAMPANA["n_tabla"] - CAMPANA["n_descartadas"]
    if len(feat) != esperadas or len(fpv) != len(feat):
        avisos.append(f"las medidas ({len(feat)} rasgos, {len(fpv)} fotos por vaca) no coinciden con las {esperadas} "
                      f"esperadas de {CAMPANA['n_fotos']} − {CAMPANA['n_tabla']} − {CAMPANA['n_descartadas']}.")
    sin_bitacora = sorted(set(feat["fila"]) - set(bit["fila"]))
    if sin_bitacora:
        avisos.append(f"filas sin bitácora: {sin_bitacora}.")

    ok = feat[(feat["estado"] == "ok") & feat["lateral_area_cm2"].notna() & feat["distancia_m"].notna()].copy()
    ok["area_corr"] = area_corregida(ok["lateral_area_cm2"], ok["distancia_m"], a.delta)
    if ok["lateral_area_cm2_corr"].notna().any():
        desv = float((ok["area_corr"] / ok["lateral_area_cm2_corr"] - 1).abs().max())
        if desv > 1e-3:
            avisos.append(f"`lateral_area_cm2_corr` del CSV difiere hasta {100 * desv:.2f} % de A·((d+{a.delta:.2f})/d)²; "
                          "el informe usa la recalculada.")
    for av in avisos:
        print(f"aviso: {av}", file=sys.stderr)

    rep = tabla_repetibilidad(ok, nombres)
    rep.to_csv(out / "repetibilidad.csv", index=False)
    figura_repetibilidad(ok, rep, out / "repetibilidad.png")

    sel = ok[ok["seleccionada_3m"] == 1]
    icc = {"todas_area": icc1(ok["fila"], np.log(ok["lateral_area_cm2"])),
           "todas_corr": icc1(ok["fila"], np.log(ok["area_corr"])),
           "sel_area": icc1(sel["fila"], np.log(sel["lateral_area_cm2"])),
           "sel_corr": icc1(sel["fila"], np.log(sel["area_corr"]))}

    rob = tabla_robustez(ok)
    rob.to_csv(out / "robustez_distancia.csv", index=False)
    curva = curva_delta(ok, DELTAS)
    curva.assign(pendiente_pct_por_m=curva["pendiente_pct_por_m"].round(3),
                 cv_intra_mediana_pct=curva["cv_intra_mediana_pct"].round(3))[
        ["delta_m", "pendiente_pct_por_m", "cv_intra_mediana_pct"]].to_csv(out / "robustez_distancia_delta.csv",
                                                                            index=False)
    delta_star = delta_cruce_cero(curva)
    figura_robustez(area_relativa(ok), rob, curva, a.delta, delta_star, out / "robustez_distancia.png")
    (out / "robustez_distancia.md").write_text(texto_robustez(rob, curva, a.delta, delta_star, len(ok),
                                                              ok["fila"].nunique()))

    ctx = {"features": feat, "fotos_por_vaca": fpv, "bitacora": bit, "ok": ok, "rep": rep, "rob": rob, "curva": curva,
           "icc": icc, "delta": a.delta, "delta_star": delta_star, "avisos": avisos,
           "p_altura": percentiles(ok["height_cm"]), "p_longitud": percentiles(ok["body_length_cm"]),
           "p_area": percentiles(ok["lateral_area_cm2"]), "p_area_corr": percentiles(ok["area_corr"])}
    if a.fotos:
        fotos = Path(a.fotos).expanduser()
        n_jpg = sum(1 for p in fotos.rglob("*") if p.suffix.lower() in (".jpg", ".jpeg"))
        if n_jpg != CAMPANA["n_fotos"]:
            print(f"aviso: {n_jpg} JPEG en {fotos}, {CAMPANA['n_fotos']} en el manifiesto de la campaña", file=sys.stderr)
        tamano, grid, _ = mosaico(feat, nombres, fotos, out / "mosaico_seleccion_3m.jpg")
        ctx["mosaico_bytes"], ctx["mosaico_grid"] = tamano, grid
        print(f"mosaico_seleccion_3m.jpg: {grid[0]}×{grid[1]} miniaturas, {tamano} bytes ({tamano / 1e6:.2f} MB)")
    (out / "resumen.md").write_text(texto_resumen(ctx))

    c0 = curva.iloc[0]
    cd = curva.iloc[int(np.argmin(np.abs(curva["delta_m"] - a.delta)))]
    print(f"medidas {len(feat)} · ok {len(ok)} · animales {ok['fila'].nunique()} · seleccionadas {len(sel)}")
    print(f"pendiente cruda {c0['pendiente_pct_por_m']:+.2f} %/m → Δ = {a.delta:.2f}: {cd['pendiente_pct_por_m']:+.2f} %/m"
          f" · Δ* = {delta_star:.3f} · CV intra {c0['cv_intra_mediana_pct']:.2f} → {cd['cv_intra_mediana_pct']:.2f} %")
    print("ICC(1) log-área todas {todas_area:.3f}/{todas_corr:.3f} · seleccionadas {sel_area:.3f}/{sel_corr:.3f}".format(
        **icc))
    print(f"-> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
