# Datos de campo — estructura canónica (jun 2026)

Pipeline de estimación de peso bovino. Identidad y pesos **validados** contra el inventario de la finca (LACAMAMI, 9 jun 2026).

## Fuentes de verdad
| Archivo | Qué es |
|---|---|
| `pesos_orden_pesaje.csv` | **Pesos de referencia (cinta bovinométrica).** 35 vacas Jersey adultas, EN ORDEN DE PESAJE, sin tags (la columna Label del CSV viejo estaba mal). `Weight (LB), Name`. |
| `WhatsApp Image 2026-06-05*.jpeg` | **fotos_hoy** — 37 fotos en orden de toma. #1-#2 = hoja en papel (sin vaca); #3-#37 = 35 vacas, 1 por vaca, marcador ArUco en poste fijo. Orden de foto = orden de pesaje. |
| `WhatsApp Image 2026-06-09 at 13.37.37.jpeg` | Inventario oficial LACAMAMI (NOMBRE ↔ ARETE TRAZABILIDAD ↔ # fotografiada). Fuente autoritativa de identidad. |
| `raw/_grouped/<NNNN>/` | Ráfagas del 4/06 (fuera del repo, en `Thesis_final_raw/`), carpeta = últimos 4 del arete leído. `mascaras/` son en su mayoría salida de YOLO (`auto_mask.py`), no manuales: 97 % coincide con el preentrenado con IoU ≥ 0.95. |
| `repesaje_1206/` | 35 fotos individuales del 12/06 (una vaca nombrada por foto) + `pesos_repesaje_12_06.csv` (segunda pesada). |
| `../val_clean/` | **Conjunto de validación anotado a mano** (40 imágenes, 3 estratos, 24 animales, `manifest.csv`). Única referencia independiente del modelo para IoU. |

## Dataset PRINCIPAL del modelo de peso → `fotos_hoy`
- `mapeo_fotos_hoy.csv` — mapeo autoritativo orden→foto→nombre→arete→peso (lo genera `build_fotos_hoy_mapping.py`).
- `features_fotos_hoy.csv` — morfometría en cm + peso, 1 fila por vaca (lo genera `src/measure_fotos_hoy.py`).
- `fotos_hoy/mascaras/`, `fotos_hoy/qa/` — máscaras y overlays de control.
- **Resultado:** modelo alométrico área→peso, leave-one-out, N=34. MAPE 7.71% (IC95 [6.2, 9.2]), R² 0.54, RMSE 33.4 kg.
- `pred_vs_real.csv`, `fig_4_4_pred_vs_real.png` — figura 4.4.

## Ráfagas de la mañana → segmentación/IoU y trabajo futuro (NO mejoran el peso)
- `features_grouped.csv` — morfometría desde las máscaras de las ráfagas (lo genera `src/measure_grouped_masks.py --masks-root …`). 497 fotos / 19 vacas pesadas. Recalculado el 10 sep 2026 con máscaras del segmentador corregido; el CSV anterior queda en `features_grouped_v1_letterbox_bug_20260609.csv`.
- Probado: ráfagas solas o combinadas DEGRADAN el modelo de peso (marcador a distancia variable → escala inconsistente). Ver `src/eval_compare_datasets.py`: ráfagas MAPE 10.17 % (R² 0.03), combinado 10.14 % (R² 0.24), frente a 7.71 % (R² 0.54) de fotos_hoy.
- Para segmentación son datos de ENTRENAMIENTO (train del fine-tuning); el IoU se mide contra `../val_clean/` (40 imágenes manuales). Resultado: el fine-tuning empeora al preentrenado; ver `../../FINETUNING.md`.
- **Máscaras (10 sep 2026):** los PNG de `_grouped/*/mascaras/` (jun 2026) se generaron con `CowSegmenter` antes de corregir el recorte del relleno del letterbox (9 sep 2026): en las ráfagas 16:9 están aplastados ~6 % en vertical. Se regeneraron con el segmentador corregido en `~/Documents/Thesis_final_raw/mascaras_regen_20260909/` (`src/auto_mask.py --all --out …`, fuera del repo, sin tocar los originales) y `features_grouped.csv` se recalculó con ellas: IoU viejo/nuevo mediano 0.925, área +5.6 %, MAPE de ráfagas 10.09 → 10.17 %. Informe: `informes/mascaras_rafagas_regen_20260910/`. El builder del `seg_dataset` sigue leyendo los PNG de junio.
- Identidad: el inventario asigna el arete 236703 a IRIS y a KARINA; las carpetas `6703*` son `IRIS/KARINA` y para el split se tratan como un solo animal (`ALIASES` en `build_yolo_seg_dataset.py`). `6706` no tiene match y se excluye de train.
- Carpetas de vacas NO pesadas (Manzanilla, Lucero, Gaby, Nahomi, Ambar, Taty, Mariposa, Estrellita, Senorita) y `6706` (arete sin match) no se usan para peso.

## Reproducir
```bash
cd pipeline
python3 build_fotos_hoy_mapping.py        # (desde raíz repo) mapeo + mosaico validación
python3 src/measure_fotos_hoy.py          # morfometría fotos_hoy -> features_fotos_hoy.csv
python3 src/eval_weight_fotos_hoy.py      # LOO + IC bootstrap -> métricas + pred_vs_real
python3 src/measure_grouped_masks.py --masks-root ~/Documents/Thesis_final_raw/mascaras_regen_20260909  # morfometría ráfagas -> features_grouped.csv
python3 src/eval_compare_datasets.py      # comparación fotos_hoy vs ráfagas vs combinado
python3 src/eval_finetuned_iou.py --visual # IoU de segmentadores contra val_clean -> informes/iou_val_manual_<fecha>/
```
