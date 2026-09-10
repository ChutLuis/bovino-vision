# Fine-tuning de YOLO26-seg — estado al 9 de septiembre de 2026

Objetivo original (Cap. 3): especializar el segmentador en las vacas Jersey de la finca con transfer
learning, split por animal y aumento de datos. Independiente del modelo de peso (no lo cambia).

## Veredicto

**El APK despliega el preentrenado COCO (`models/yolo26n-seg.pt`, clase 19).** El fine-tuning se
implementó, se evaluó contra un conjunto de validación anotado a mano y **empeoró** al segmentador.
El resultado negativo es el entregable: cierra la promesa del Cap. 3 con evidencia y deja el
instrumento validado (IoU 0.86 y MAPE 7.71 % de la tesis) sin cambios.

Evaluación sobre las 40 imágenes manuales (24 animales, ninguno en train), PNG pintados como
referencia, conf 0.45, imgsz 640, selección "mayor área" como en el pipeline de peso
(`informes/iou_val_manual_20260909/resumen.md`):

| modelo | eligió la vaca objetivo | sin detección | IoU vaca objetivo | error de área medio | recall de instancias |
|---|---|---|---|---|---|
| preentrenado COCO | 92.5 % | 1 / 40 | **0.851** (fácil 0.929 · media 0.780 · difícil 0.841) | +4.1 % | 0.85 |
| afinado 10 jun 2026 | 82.5 % | 6 / 40 | 0.725 (0.830 · 0.756 · 0.520) | −13.2 % | 0.57 |

Bootstrap por animal (n = 24, 5000 remuestreos) de la diferencia afinado − preentrenado en IoU de la
vaca objetivo: **−0.13, IC95 [−0.23, −0.03]**. El afinado no detecta nada en 6 fotos, entre ellas dos
laterales limpias del protocolo del producto (`5_06_ford`, `12_06_selena`).

Por qué pasa, dos defectos en las etiquetas de entrenamiento:
1. De las 377 máscaras de ráfaga que alimentan train, el 97 % coincide con la salida del propio
   preentrenado con IoU ≥ 0.95 (mediana 0.987): fueron generadas por `auto_mask.py`, no a mano.
   El fine-tuning es auto-destilación sobre 12–14 animales y solo puede empatar o desviarse.
2. Esas máscaras se guardaron con un error geométrico: `core/segmenter.py` redimensionaba `masks.data`
   (que está a la resolución de entrada de la red, con relleno) sin recortar el relleno, y en las ráfagas
   16:9 (4096×2304) la silueta quedaba aplastada un 6 % en vertical. Corregido el 9 sep 2026
   (`ops.scale_masks`, prueba `tests/test_segmenter_padding.py`). Las fotos 4:3 del producto y de
   `fotos_hoy` no se vieron afectadas. Los PNG de `_grouped/*/mascaras/` siguen aplastados hasta que se
   regeneren.

La ruta del APK (LiteRT, letterbox 640×640 fijo, `core/segmenter_litert.py`) evaluada sobre las mismas
40 imágenes con el umbral del producto (conf 0.5): IoU 0.868, eligió la vaca objetivo en 38 de 40,
ninguna sin detección; detecta las dos fotos del 12/06 (`karina`, `oscarina`) que el `.pt` con
letterbox rectangular pierde a ese umbral (`informes/iou_val_manual_apk_20260909/`).

## Conjunto de validación manual (`data/val_clean/`)

40 imágenes anotadas con `annotate_val.py` (MobileSAM guiado por clics + pincel; ninguna máscara
proviene de YOLO), estratificadas: 15 fáciles (laterales controladas 5/06), 15 medias (ráfagas con
varias vacas y repesaje 12/06), 10 difíciles (oclusión, multi-vaca, fallos conocidos). Por foto:
`images/{qid}.*`, `masks/{qid}_inst{k}.png` (inst0 = vaca pesada), `labels/{qid}.txt` (una línea por
instancia), fila en `manifest.csv`. Los animales del manifiesto quedan fuera de train.

## Pasos (reproducibles)

```bash
cd pipeline

# 1) Dataset YOLO-seg, split por animal. Verifica fuga por nombre, arete y sha256; --dry-run no escribe.
python3 src/build_yolo_seg_dataset.py --dry-run
python3 src/build_yolo_seg_dataset.py            # -> data/field/seg_dataset/{images,labels}/{train,val} + data.yaml
#   ráfagas en --raw / $BOVINO_RAW_GROUPED / data/field/raw/_grouped / ~/Documents/Thesis_final_raw/raw/_grouped
#   plan actual: train 352 imágenes de 12 animales; val 40 (86 instancias) de 24 animales
#   IRIS se excluye de train porque comparte arete 236703 con KARINA (val); unk_6706 se excluye por no tener identidad

# 2) Entrenar (opcional). CPU: 61–82 s/época con 390 imágenes; 50 épocas ≈ 1 h.
python3 src/finetune_segmenter.py --freeze 10 --optimizer AdamW --lr0 0.0005 --epochs 30
#   -> runs/segment/runs/seg_finetune_jersey/weights/best.pt  y  models/finetuned_<fecha>_<sha8>.pt (nunca sobrescribe)
#   con --optimizer auto (default) Ultralytics ignora --lr0 y usa AdamW lr 0.002

# 3) Evaluar contra las máscaras manuales (informe + paneles visuales)
python3 src/eval_finetuned_iou.py --models pre=models/yolo26n-seg.pt:19 nuevo=models/finetuned_<fecha>_<sha8>.pt:0 --visual
```

Criterio para que un modelo afinado sustituya al preentrenado: no-inferioridad en IoU de la vaca
objetivo (límite inferior del IC95 de la diferencia > −0.02), cero fotos fáciles sin detección, y
después la Fase E: paridad de área PC↔APK ≤ 1 % y reajuste de los coeficientes a, b del modelo de
peso, porque se ajustaron con áreas del preentrenado (que sobre-segmenta +4.3 % frente a la
anotación manual en las laterales controladas).

## Qué cambió respecto a la versión anterior de este documento

- Ya no hay "790 máscaras tuyas": las máscaras de ráfaga son salida de YOLO; las manuales son las 40 de val.
- El split ya no es 614/176 con 6 animales held-out: es 352/40 con 24 animales held-out (más IRIS por arete).
- La ruta de pesos `runs/seg_finetune/jersey/` no existe: Ultralytics 8.4 escribe en `runs/segment/runs/<name>/`.
- `eval_finetuned_iou.py` se reescribió: antes leía el label completo como una sola línea y reventaba con
  etiquetas multi-instancia; ahora usa los PNG, empareja instancias y reporta IC por animal.
- El caveat "sin GT manual no afirmes nada" quedó resuelto por `annotate_val.py`; la afirmación que
  habilita es la de arriba.

## Historial

- 10 jun 2026: fine-tuning de 80 épocas (ultralytics 8.4.53) sobre el dataset viejo → `models/yolo26n-seg-finetuned.pt`
  (copia `models/finetuned_20260610_d6c65749.pt`). mAP50(M) 0.92 sobre su val automático; 0.718 de IoU sobre el manual.
- 27 ago 2026: tres corridas de 1 época en CPU (warmup) en `runs/segment/runs/`. Sin valor.
- 2 y 9 sep 2026: anotación manual de las 40 imágenes de validación.
- 9 sep 2026: evaluación, cierre y este documento. Detalle en `docs/correcciones/revision_finetune_2026-09-09.md`.
