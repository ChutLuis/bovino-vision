# Modelo de peso de la campaña de calibración

Referencias: 40 animales, cinta bovinométrica; una lectura por una experta, fecha 2026-09-20; fotografías del 2026-09-12. Una fotografía por animal: la primaria o, si la ruta la rechazó, la siguiente aceptada del orden de preselección. Sustituciones: fila 7 (sin_vaca en la primaria; entra `IMG_20260912_070835.jpg`, orden 3). Exclusiones: ninguna.

| Análisis | n | MAPE % | IC95 % | MAE kg | RMSE kg | R² | Cobertura IP95 |
|---|---|---|---|---|---|---|---|
| Una fotografía por animal (primario) | 40 | 7.72 | [5.98, 9.57] | 29.0 | 36.1 | 0.36 | 97.5 % |
| Mediana de las fotografías aceptadas por animal (secundario) | 40 | 7.80 | [6.02, 9.63] | 29.4 | 36.4 | 0.35 | 97.5 % |

H1a (MAPE < 10 %): valor puntual sí; límite superior del IC95 sí.

Ajuste completo del primario: a = 2.341031046, b = 0.5347334325; σ_log = 0.0924, t = 2.0244, rango de calibración 9808–16899 cm².
AIC área -73.1 frente a área + caja -74.8 (Δ = -1.7); comparación secundaria, no elige el bundle.
Repetibilidad entre fotografías del mismo animal: ICC(1) del log del área 0.978; CV del peso predicho mediana 0.85 %, máximo 3.52 %.

Bundle `campana-994d9c2cd1a6` escrito con `golden_cases.json` (10 casos, tolerancia 1e-8 kg).

Alcance: validación interna por animal en un hato y un protocolo de captura; la referencia es cinta bovinométrica, no báscula. Archivos: `evaluacion.json`, `predicciones_loo.csv`, `pred_vs_real.png`.
