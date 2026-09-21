# Robustez a la distancia y corrección de paralaje

Fotografías con `estado == ok`: 1180 de 40 animales, en tres niveles nominales (2.5, 3.0 y 3.5 m). Distancia por fotografía `d = f_px·0.15/marker_px`, con `f_px = W·f35/36` (EXIF); nivel = el más cercano (cortes 2.75 y 3.25 m).

## Método

- **Área relativa** por fotografía: área / mediana del mismo animal en el nivel 3.0 m. **Cociente por nivel**: mediana entre animales de (mediana del animal en el nivel) / (mediana del animal a 3.0 m); solo animales con fotografías en ambos niveles.
- **Pendiente** (%/m): regresión de `log(A·((d+Δ)/d)²)` sobre `d` con efectos fijos por animal (ambas variables centradas dentro de cada animal, pendiente común), ×100. Error estándar con N − k − 1 grados de libertad.
- **CV intra mediana**: mediana entre animales del coeficiente de variación de `A_corr(Δ)` sobre todas sus fotografías `ok`.
- **Δ\***: valor de Δ donde la pendiente cruza cero, por interpolación lineal entre dos puntos consecutivos de la malla Δ ∈ {0.0, 0.1, …, 1.0} m.

## Cociente de área por nivel (`robustez_distancia.csv`)

| nivel (m) | fotografías ok | animales | cociente área cruda | cociente área corregida |
|---|---|---|---|---|
| 2.5 | 439 | 35 | 0.9343 | 0.9950 |
| 3.0 | 410 | 40 | 1.0000 | 1.0000 |
| 3.5 | 331 | 33 | 1.0287 | 0.9829 |

## Pendiente según Δ (`robustez_distancia_delta.csv`)

| Δ (m) | pendiente (%/m) | error estándar (%/m) | CV intra mediana (%) |
|---|---|---|---|
| 0.0 | +9.6 | 0.32 | 4.97 |
| 0.1 | +7.3 | 0.31 | 4.57 |
| 0.2 | +5.2 | 0.31 | 4.05 |
| 0.3 | +3.2 | 0.30 | 3.64 |
| 0.4 | +1.3 | 0.30 | 3.69 |
| 0.5 ← | -0.4 | 0.30 | 3.67 |
| 0.6 | -2.1 | 0.30 | 3.56 |
| 0.7 | -3.7 | 0.30 | 3.69 |
| 0.8 | -5.1 | 0.30 | 3.97 |
| 0.9 | -6.5 | 0.29 | 4.38 |
| 1.0 | -7.9 | 0.29 | 4.79 |

Pendiente cruda (Δ = 0): +9.6 %/m (e.e. 0.32); con Δ = 0.50 m: -0.4 %/m (e.e. 0.30). CV intra mediana: 5.0 % → 3.7 %. Δ\* (cruce por cero) = 0.48 m.

## Lectura

1. **Tendencia cruda.** El área lateral crece +9.6 %/m con la distancia dentro de cada animal. El marcador se sostiene junto al costado, delante del plano de la silueta: la escala px/cm se sobreestima más cuanto más cerca está la cámara y el área en cm² se subestima más de cerca. Parte del efecto puede venir de la máscara a menor escala (el segmentador ve la silueta con menos píxeles a 3.5 m), por lo que la corrección se presenta como empírica.
2. **Corrección `A_corr = A·((d+Δ)/d)²` con Δ = 0.50 m.** Fórmula única y continua en `d`, no por tramos: no introduce saltos en los cortes 2.75 y 3.25 m y se aplica igual a cualquier distancia dentro del rango. Δ se calibró por invarianza intra-animal, sin pesos: la pendiente residual pasa a -0.4 %/m (Δ\* = 0.48 m) y el CV intra mediana baja de 5.0 % a 3.7 %.
3. **Cruda o corregida.** Se conservan las dos columnas (`lateral_area_cm2`, `lateral_area_cm2_corr`); la invarianza a la distancia no decide por sí sola cuál predice mejor el peso. El modelo de peso usa el área cruda de una fotografía por animal, fijado antes de recibir los pesos (`eval_weight_campana.py`); la corregida queda como análisis de robustez.
4. **Uso de las fotografías.** El modelo principal usa una fotografía por animal: la primaria, la aceptada más cercana a 3.0 m, o la siguiente aceptada del orden de preselección si la ruta rechazó la primaria; las cinco más cercanas sirven para la repetibilidad y el análisis secundario de medianas, y todas las `ok` para esta robustez a la distancia.
