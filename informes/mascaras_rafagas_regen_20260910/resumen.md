# Regeneración de las máscaras de ráfagas con el segmentador corregido — 2026-09-10

**Por qué.** `CowSegmenter` no recortaba el relleno del letterbox (corregido en el commit 0fd6669, 9 sep 2026):
en las ráfagas 16:9 (4096×2304) las máscaras de `_grouped/*/mascaras/` salían aplastadas ~6 % en vertical y
`features_grouped.csv` (9 jun 2026) heredaba alturas y áreas subestimadas. `fotos_hoy` (4:3) no estaba afectado.

**Qué se hizo.** `src/auto_mask.py --all --out /home/luisc/Documents/Thesis_final_raw/mascaras_regen_20260909` (modelo `models/yolo26n-seg.pt`,
conf 0.45, vaca de mayor área; `run_info.json`) segmentó las 825 fotos de las 39 carpetas y escribió las máscaras
en un directorio nuevo, fuera del repo y sin tocar los PNG originales (respaldo `mascaras_backup.zip`).
Triage (`triage.csv`): lista = 52, revisar = 733, sin_marcador = 33, sin_vaca = 7.

## Máscaras viejas vs nuevas (`src/compare_mask_sets.py`, `comparacion_mascaras.csv`)

| métrica (nueva/vieja) | mediana | p5 | p95 |
|---|---|---|---|
| IoU | 0.9251 | 0.8867 | 0.9383 |
| área | 1.0561 | 1.0343 | 1.0655 |
| alto de la silueta | 1.0408 | 1.0101 | 1.0634 |
| ancho de la silueta | 0.9855 | 0.9659 | 1.0088 |

Pares comparados: 790. Solo en el juego viejo: 0. Solo en el nuevo: 28 (fotos que antes quedaron sin
máscara). IoU < 0.90 en 63 pares; IoU < 0.50 en 1 (`6705/IMG_20260604_070151_1`: 5 vacas en cuadro, la de mayor
área cambia de animal). El alto crece ~4 % de mediana y el área ~5.6 %, en línea con el 6 % predicho por la geometría
del letterbox (el ancho baja ~1.5 % porque la máscara vieja se estiraba en horizontal al reescalar sin recorte).

## Efecto en el modelo de peso (`src/measure_grouped_masks.py --masks-root …` → `src/eval_compare_datasets.py`)

Mismas 497 fotos / 19 vacas pesadas que antes (19 descartadas sin marcador). Leave-one-out por animal, mediana por vaca:

| conjunto | modelo | antes (máscaras con bug) | ahora (corregidas) |
|---|---|---|---|
| A) fotos_hoy (N=34) | área log-log | 7.71 % · R² 0.54 | 7.71 % · R² 0.54 (no cambia) |
| B) ráfagas (N=19) | área log-log | 10.09 % [7.5, 12.7] · R² 0.04 · RMSE 42.3 | **10.17 % [7.5, 12.8] · R² 0.03 · RMSE 42.7** |
| B) ráfagas (N=19) | lineal 6 rasgos | 10.13 % · R² 0.11 | 11.65 % · R² −0.18 |
| C) combinado (N=36) | área log-log | 10.13 % [8.0, 12.3] · R² 0.24 | **10.14 % [8.1, 12.2] · R² 0.24** |

**Lectura.** El bug era sistemático (misma proporción en todas las fotos 16:9), así que corregirlo reescala las
áreas sin cambiar el orden entre animales; el modelo log-log absorbe el factor en el intercepto y el MAPE se mueve
0.08 puntos. La conclusión de la tesis se mantiene: las ráfagas no mejoran el modelo de peso (escala inconsistente
por el marcador a distancia variable), y `fotos_hoy` sigue siendo el conjunto principal.

## Archivos

- `data/field/features_grouped.csv`: recalculado con las máscaras corregidas (canónico desde hoy).
- `data/field/features_grouped_v1_letterbox_bug_20260609.csv`: copia del CSV anterior, para trazabilidad.
- Máscaras nuevas: `/home/luisc/Documents/Thesis_final_raw/mascaras_regen_20260909` (fuera del repo, 818 PNG). Las de `_grouped/*/mascaras/` siguen siendo las de junio;
  `build_yolo_seg_dataset.py` las usa como etiquetas de train (el fine-tuning está cerrado; si se reabriera, habría que
  apuntarlo a las corregidas).

## Reproducir

```
cd pipeline
.venv/bin/python src/auto_mask.py --all --out ~/Documents/Thesis_final_raw/mascaras_regen_20260909    # ~6 min CPU; reanudable
.venv/bin/python src/compare_mask_sets.py --new ~/Documents/Thesis_final_raw/mascaras_regen_20260909 --out informes/mascaras_rafagas_regen_20260910
.venv/bin/python src/measure_grouped_masks.py --masks-root ~/Documents/Thesis_final_raw/mascaras_regen_20260909 --out data/field/features_grouped.csv
.venv/bin/python src/eval_compare_datasets.py
```
