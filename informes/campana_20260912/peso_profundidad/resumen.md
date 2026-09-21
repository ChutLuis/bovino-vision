# Modelo de peso por profundidad corporal proyectada

Referencias: 40 animales, cinta bovinométrica; fotografías del 2026-09-12. Una fotografía por animal, la misma selección que usa el modelo de área. Predictor: profundidad corporal proyectada media de la banda central (`D_media`), en cm, medida por la ruta de la aplicación. Exponente fijo en 1.0: se ajusta solo el coeficiente.

| Modelo | n | MAPE % | IC95 % | MAE kg | RMSE kg | R² | Cobertura IP95 | Ancho IP95 mediano kg |
|---|---|---|---|---|---|---|---|---|
| Profundidad `W = a·D_media` | 40 | 6.54 | [5.01, 8.18] | 24.8 | 31.9 | 0.50 | 97.5 % | 129 |
| Área `W = a·A^b` (referencia) | 40 | 7.72 | [5.98, 9.57] | 29.0 | 36.1 | 0.36 | 97.5 % | 147 |

Comparación pareada por animal: ΔMAPE = -1.18 puntos [-2.18, -0.25] (bootstrap de animales, B = 5000); mejora en 25 de 40 animales; el intervalo excluye el cero.

Influencia: sin fila 12, fila 35, fila 31 (los tres que más favorecen a la profundidad) y reajustando ambos modelos en 37 animales, Δ′ = -0.76 [-1.71, +0.15]; conserva 64 % de la ganancia.

k-fold agrupado por animal (k = 5, 20 repeticiones): MAPE medio 6.51 % (sd 0.11, rango 6.39–6.72); coincide con el LOAO, así que el resultado no depende del tamaño del pliegue.

Ajuste completo: a = 5.740670748, b = 1 (fijo); σ_log = 0.0824 con 39 grados de libertad, t = 2.0227, rango de calibración 55.9–76.4 cm de profundidad.

El semiancho del intervalo conserva el término de apalancamiento del esquema de dos parámetros, que un modelo de exponente fijo no necesita: lo ensancha hasta un 4.6 % en los extremos del rango y nada en el centro. Se mantiene para no cambiar el esquema que la aplicación valida, y la cobertura medida (97.5 %) se reporta tal cual.

Bundle `campana-depth-994d9c2cd1a6` con `golden_cases.json` (10 casos, tolerancia 1e-8 kg) y `golden_depth_fotos.json` (10 fotografías reales con el sha256 de su máscara).

Alcance: validación interna por animal en un hato y un protocolo de captura; la referencia es cinta bovinométrica, no báscula. La profundidad se definió sobre estas mismas siluetas, así que su evaluación es contemporánea, no independiente. Archivos: `evaluacion.json`, `predicciones_loo.csv`, `pred_vs_real.png`, `comparacion_pareada.png`.
