# Campaña de calibración — La Primavera, 12 de septiembre de 2026

La Primavera; 40 animales Jersey; unas 30 fotografías por animal (mín 15, máx 42) a 2.5, 3.0 y 3.5 m, con el marcador ArUco id 0 de 15 cm sostenido junto al costado del animal. 1226 fotografías: 1202 Xiaomi 15 Ultra (4096×3072, equiv. 23 mm) y 24 Galaxy A25 (4080×3060, equiv. 27 mm); 27 de la tabla de registro entre animales y 1 suelta descartada, así que quedan 1198 medidas (Xiaomi 15 Ultra 1174 / Galaxy A25 24). Animales fotografiados solo con el Galaxy A25: 40 (Esmeralda). Los pesos de referencia los conserva la finca; la categoría no se registró.

Distancia por fotografía `d = f_px·0.15/marker_px`, con `f_px = W·f35/36` (EXIF `FocalLengthIn35mmFilm`); nivel de distancia = el más cercano de {2.5, 3.0, 3.5} m (cortes 2.75 y 3.25). Corrección de paralaje del marcador `A_corr = A·((d+Δ)/d)²`, Δ = 0.50 m; solo se corrige el área. Escala: 15 cm / lado medio del marcador.

## Decodificación

| paso | fotografías | % de las medidas |
|---|---|---|
| medidas (fotos por vaca) | 1198 | 100.0 |
| marcador ArUco id 0 detectado | 1194 | 99.7 |
| vaca segmentada | 1181 | 98.6 |
| `ok` (marcador, vaca y silueta completa) | 1180 | 98.5 |

Estados: `ok` 1180, `sin_marcador` 1, `sin_vaca` 17, `silueta_cortada` 0. Por teléfono: Xiaomi 15 Ultra 1174 medidas, 1156 `ok`; Galaxy A25 24 medidas, 24 `ok`.
Centro del marcador dentro de la caja de la vaca: 416/1180 de las `ok`; 90/200 de las seleccionadas a 3.0 m.

## Distribución por nivel de distancia

| nivel (m) | fotografías | `ok` | animales con `ok` | d de las `ok`: mediana (mín–máx) |
|---|---|---|---|---|
| 2.5 | 439 | 439 | 35 | 2.50 (1.82–2.75) |
| 3.0 | 412 | 410 | 40 | 3.03 (2.75–3.25) |
| 3.5 | 343 | 331 | 33 | 3.59 (3.25–4.03) |
| sin marcador | 4 | — | — | — |

## Morfometría implícita (`estado == ok`, n = 1180)

| medida | p2.5 | p5 | p50 | p95 | p97.5 |
|---|---|---|---|---|---|
| altura (cm) | 114.0 | 117.7 | 130.3 | 146.7 | 148.9 |
| longitud del cuerpo (cm) | 158.9 | 170.5 | 213.6 | 238.5 | 242.5 |
| área lateral cruda (cm²) | 9027 | 9499 | 14002 | 16887 | 17198 |
| área lateral corregida (cm²) | 13331 | 13707 | 19246 | 22526 | 23029 |

Rango de plausibilidad de la longitud recalibrado con la campaña: [159, 243] cm (p2.5–p97.5 sobre las 1180 medidas `ok`). El rango del piloto (`PLAUS_LEN` 110–190 cm en `measure_fotos_hoy.py`, con el marcador en el poste) no se aplica a estas medidas.

## Selección a 3.0 m

Por animal, las 5 fotografías `ok` con menor |d − 3.0| (desempate por nombre de archivo). Animales con 5 seleccionadas: 40/40; con menos: 0. Distancia de las 200 seleccionadas: mediana 3.04 m (2.62–3.26); por nivel: 2.5 m → 5, 3.0 m → 189, 3.5 m → 6.

## Decisión → evidencia

| decisión | evidencia |
|---|---|
| Corrección de paralaje `A_corr = A·((d+Δ)/d)²` con Δ = 0.50 m, fórmula única y continua (no por tramos) | Pendiente intra-animal de log(área) sobre d: +9.6 %/m cruda → -0.4 %/m con Δ = 0.50 (cruce por cero en Δ\* = 0.48 m); CV intra mediana 5.0 % → 3.7 %; cocientes por nivel 2.5/3.5 m: cruda 0.934/1.029, corregida 0.995/0.983 (`robustez_distancia.md`, `robustez_distancia_delta.csv`). Corrección empírica: el marcador va delante del plano de la silueta y parte del efecto puede venir de la máscara a menor escala. |
| Preselección de las 5 fotografías por animal más cercanas a 3.0 m; la primaria es la más cercana | 40/40 animales con 5; d mediana 3.04 m; ICC(1) del log-área en las seleccionadas 0.977 (cruda) / 0.977 (corregida) frente a 0.893 / 0.929 con todas; CV intra mediana en las seleccionadas 1.5 % / 1.6 % (`repetibilidad.csv`). |
| Se conservan el área cruda y la corregida | El modelo de peso usa el área cruda de una fotografía por animal (protocolo fijado antes de los pesos, `eval_weight_campana.py`); la corregida documenta la robustez a la distancia y no entra al modelo. |
| Todas las fotografías `ok` sirven para la robustez a la distancia | 1180 medidas `ok` en tres niveles (439/410/331 a 2.5/3.0/3.5 m), 40 animales (`robustez_distancia.csv`). |

## Pesos

Pesos de referencia del 20 de septiembre de 2026: cinta bovinométrica, una lectura por animal, 40 animales (`pesos_20260920.csv`; también en `peso_lb1`/`peso_kg` de la bitácora). El ajuste y la validación del modelo de peso están en `peso/` (`eval_weight_campana.py` y `weight_stats_campana.py`): una fotografía por animal (la primaria o, si la ruta la rechazó, la siguiente aceptada del orden de preselección), área cruda de la ruta de la aplicación, leave-one-out por animal.

## Repetibilidad

| conjunto | fotografías | animales | ICC(1) log(área) | ICC(1) log(área corregida) | CV intra mediana área (%) | CV intra mediana área corregida (%) |
|---|---|---|---|---|---|---|
| todas las `ok` | 1180 | 40 | 0.893 | 0.929 | 5.0 | 3.7 |
| seleccionadas a 3.0 m | 200 | 40 | 0.977 | 0.977 | 1.5 | 1.6 |

ICC(1) de una vía para grupos desbalanceados: `(MSB − MSW) / (MSB + (n0 − 1)·MSW)`, con `n0 = (N − Σn_i²/N)/(k − 1)`. El ICC del log-área coincide con el ICC del log-peso para cualquier modelo alométrico `log peso = log a + b·log área` (transformación afín). Detalle por animal en `repetibilidad.csv`; `repetibilidad.png` muestra el área corregida por animal (todas las `ok` en gris, seleccionadas en azul, mediana en negro).

## Archivos

- `repetibilidad.csv`, `repetibilidad.png`: por animal, n y CV intra del área cruda y corregida (todas / seleccionadas).
- `robustez_distancia.csv`, `robustez_distancia_delta.csv`, `robustez_distancia.png`, `robustez_distancia.md`: cociente por nivel, curva Δ → pendiente y lectura.

## Reproducir

```
cd pipeline
.venv/bin/python src/build_campana_csvs.py            # bitácora y fotos por vaca desde la separación por animal
.venv/bin/python src/measure_campana.py               # rasgos por fotografía; overlays QA fuera del repo
.venv/bin/python src/report_campana.py --fotos $BOVINO_CAMPANA_RAW      # crudos fuera del repositorio
.venv/bin/python src/eval_weight_campana.py --out ../informes/campana_20260912/peso   # modelo de peso
.venv/bin/python src/weight_stats_campana.py          # estadística complementaria en peso/estadistica_extra
```
