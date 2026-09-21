# Pipeline (PC)

Código Python de la tesis: anotación, segmentación, morfometría, modelo de peso, evaluaciones y exportación del
modelo que consume la app. Todo el entrenamiento y la validación ocurren aquí; el teléfono solo ejecuta artefactos
congelados (`app/assets/model_bundle/`).

## Instalación

```bash
cd pipeline
python3 -m venv .venv
.venv/bin/pip install -r requirements-lock.txt   # versiones exactas con las que se validó (Python 3.12, CPU)
.venv/bin/python -m pytest -q                     # tests/; el smoke test E2E con cámara se corre a mano (pytest.ini)
```

`requirements.txt` conserva rangos amplios compatibles con la Jetson; `requirements-lock.txt` fija lo que se usó para
exportar el `.tflite`, emular la ruta del APK en PC y evaluar IoU y paridad.

## Scripts por propósito (`src/`)

| Propósito | Scripts |
|---|---|
| Datos de campo | `group_by_burst.py` (ráfagas por vaca), `triage_photos.py`, `build_master_logbook.py`, `extract_features.py`, `build_dataset.py` |
| Anotación de máscaras | `annotate_val.py` (MobileSAM + pincel; conjunto de validación), `build_val_clean.py`, `draw_mask.py`, `annotate_sam.py`, `select_cow.py`, `review_masks.py`, `auto_mask.py` (máscaras automáticas de las ráfagas), `compare_mask_sets.py` |
| Segmentador | `build_yolo_seg_dataset.py` (dataset YOLO-seg con split por animal; `--dry-run` no escribe), `finetune_segmenter.py`, `eval_finetuned_iou.py` (IoU contra las máscaras manuales, IC por animal), `eval_segmenter_parity.py` (`.pt` vs LiteRT en PC vs Galaxy A25), `eval_cow_selection.py` (regla con varias vacas), `make_model_manifest.py` (ficha del `.tflite` para la app) |
| Escala ArUco | `generate_markers.py`, `validate_scale.py`, `eval_aruco_parity.py` (js-aruco2 vs OpenCV) |
| Modelo de peso | `measure_fotos_hoy.py`, `measure_grouped_masks.py`, `eval_weight_fotos_hoy.py` (leave-one-out, IC bootstrap), `eval_compare_datasets.py`, `train_weight_model.py` |
| Captura autónoma (prototipo Jetson) | `capture.py`, `detect_live.py`, `analyze_batch.py`, `benchmark_jetson.py`, `config.yaml` |
| Campaña de calibración (sep 2026) | `build_campana_csvs.py` (bitácora y fotografías por animal), `measure_campana.py` (morfometría, distancia estimada y corrección de paralaje por fotografía), `report_campana.py` (`informes/campana_20260912/`), `eval_weight_campana.py` (una fotografía por animal, la primaria o la siguiente aceptada del orden de preselección; área cruda de la ruta de la aplicación, leave-one-out por animal, IC95 bootstrap, intervalo de predicción, AIC, ICC; escribe `weight_model.json` y `golden_cases.json`), `weight_stats_campana.py` (k-fold agrupado repetido, bootstrap de a y b, Bland–Altman, CCC, modelo del piloto sin reajuste, cinta de junio) |
| Jornada de campo | `generate_field_guide.py` (guía imprimible) |

`src/core/`: `aruco.py`, `calibration.py`, `cow_detector.py`, `segmenter.py` (Ultralytics `.pt`),
`segmenter_litert.py` (reproduce en Python la ruta del APK: letterbox 640×640, LiteRT, postproceso de la máscara),
`morphometry.py`, `seg_eval.py`, `trigger.py`, `storage.py`.

## Pruebas (`tests/`)

`pytest -q` cubre el parseo de etiquetas y las métricas (`test_seg_eval.py`), el split sin fuga
(`test_split_integrity.py`), el manifiesto del conjunto de validación (`test_val_manifest.py`), el contrato del
`.tflite` con su manifiesto (`test_export_contract.py`), el recorte del relleno del letterbox
(`test_segmenter_padding.py`), la emulación LiteRT (`test_segmenter_litert.py`) y su paridad con lo medido en el A25
(`test_parity_a25.py`, sobre `informes/benchmark_a25_20260826_fullres.json`), además de la morfometría
(`test_morphometry_smoke.py`) y la campaña de calibración: `test_measure_campana.py` (distancia, niveles, corrección y selección a 3 m), `test_eval_weight_campana.py` (ajuste cerrado, intervalo por álgebra matricial, LOO sin fuga, validación de referencias, recorrido sintético y reproducción exacta del bundle de la app desde los datos de la campaña), `test_weight_stats_campana.py` (LOO, k-fold, CCC, Bland–Altman) y `test_report_campana.py` (pendiente por distancia e ICC sobre datos sintéticos). `test_pipeline_smoke.py` es un E2E con cámara y se corre a mano.

## Datos y modelos

- `data/field/`: fotos curadas de junio de 2026, pesos y morfometría (`data/field/README_DATASETS.md`).
- `data/field/campana_20260912/`: bitácora, fotografías por animal y medidas por fotografía de la campaña de calibración del 12 de septiembre de 2026; los crudos (1226 JPG, `MANIFEST.sha1`) quedan fuera del repositorio y se indican con `--fotos` o `$BOVINO_CAMPANA_RAW`.
- `data/val_clean/`: 40 imágenes de validación anotadas a mano, con `manifest.csv`.
- `data/field/seg_dataset/`: lo genera el builder; no se versiona.
- Crudos (ráfagas `_grouped/`): fuera del repositorio, archivo `Thesis_final_raw/` con `MANIFEST.sha1` (`--raw` o `$BOVINO_RAW_GROUPED`); los
  scripts los toman de `--raw`, `$BOVINO_RAW_GROUPED` o esa ruta.
- `models/`: pesos no versionados; `models/README.md` lista procedencia y sha256. El segmentador desplegado es el
  YOLO26n-seg preentrenado en COCO exportado a LiteRT FP32 (sha256 `14b35a7b…`); el fine-tuning se evaluó contra las
  máscaras manuales y se descartó (`FINETUNING.md`).

## Notebook de evidencia

`notebooks/modelo_peso.ipynb` (raíz del repositorio) reproduce con las funciones de `eval_weight_fotos_hoy.py` el
modelo de peso y reúne IoU, paridad, tiempos del A25 y golden a partir de `informes/`. Se ejecuta con este entorno más
`ipykernel` (`requirements.txt`).

## Jetson Orin Nano

Fue la plataforma del prototipo de captura autónoma (mayo de 2026): `capture.py` detecta marcador y vaca con la
cámara USB y guarda ráfagas. El producto final es la app; la Jetson queda como línea futura de estación de corral.
`JETSON_SETUP.md` documenta el entorno (PyTorch de NVIDIA, cuSPARSELt, numpy 1.x, torchvision desde fuente).
