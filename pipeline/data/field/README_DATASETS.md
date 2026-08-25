# Datos de campo — estructura canónica (jun 2026)

Pipeline de estimación de peso bovino. Identidad y pesos **validados** con el autor.

## Fuentes de verdad
| Archivo | Qué es |
|---|---|
| `pesos_orden_pesaje.csv` | **Pesos de referencia (cinta bovinométrica).** 35 vacas Jersey adultas, EN ORDEN DE PESAJE, sin tags (la columna Label del CSV viejo estaba mal). `Weight (LB), Name`. |
| `WhatsApp Image 2026-06-05*.jpeg` | **fotos_hoy** — 37 fotos en orden de toma. #1-#2 = hoja en papel (sin vaca); #3-#37 = 35 vacas, 1 por vaca, marcador ArUco en poste fijo. Orden de foto = orden de pesaje. |
| `WhatsApp Image 2026-06-09 at 13.37.37.jpeg` | Inventario oficial LACAMAMI (NOMBRE ↔ ARETE TRAZABILIDAD ↔ # fotografiada). Fuente autoritativa de identidad. |
| `raw/_grouped/<NNNN>/` | Ráfagas de la mañana, carpeta = últimos 4 del arete leído. Máscaras anotadas a mano en `mascaras/`. |

## Dataset PRINCIPAL del modelo de peso → `fotos_hoy`
- `mapeo_fotos_hoy.csv` — mapeo autoritativo orden→foto→nombre→arete→peso (lo genera `build_fotos_hoy_mapping.py`).
- `features_fotos_hoy.csv` — morfometría en cm + peso, 1 fila por vaca (lo genera `src/measure_fotos_hoy.py`).
- `fotos_hoy/mascaras/`, `fotos_hoy/qa/` — máscaras y overlays de control.
- **Resultado:** modelo alométrico área→peso, leave-one-out, N=34. MAPE 7.71% (IC95 [6.2, 9.2]), R² 0.54, RMSE 33.4 kg.
- `pred_vs_real.csv`, `fig_4_4_pred_vs_real.png` — figura 4.4.

## Ráfagas de la mañana → segmentación/IoU y trabajo futuro (NO mejoran el peso)
- `features_grouped.csv` — morfometría desde las máscaras manuales (lo genera `src/measure_grouped_masks.py`). 497 fotos / 19 vacas pesadas.
- Probado: ráfagas solas o combinadas DEGRADAN el modelo de peso (marcador a distancia variable → escala inconsistente). Ver `src/eval_compare_datasets.py`. Sirven para IoU (n=40) y futuro fine-tuning de YOLO26-seg.
- Carpetas de vacas NO pesadas (Manzanilla, Lucero, Gaby, Nahomi, Ambar, Taty, Mariposa, Estrellita, Senorita) y `6706` (arete sin match) no se usan para peso.

## Reproducir
```bash
cd prototype
python3 build_fotos_hoy_mapping.py        # (desde raíz repo) mapeo + mosaico validación
python3 src/measure_fotos_hoy.py          # morfometría fotos_hoy -> features_fotos_hoy.csv
python3 src/eval_weight_fotos_hoy.py      # LOO + IC bootstrap -> métricas + pred_vs_real
python3 src/measure_grouped_masks.py      # morfometría ráfagas -> features_grouped.csv
python3 src/eval_compare_datasets.py      # comparación fotos_hoy vs ráfagas vs combinado
```

Material superado movido a `junk/data_field_obsoleto/` en la raíz del repo (ver `junk/README.md`).
