# Modelos (no versionados en git: `pipeline/models/*.pt` está en .gitignore)

| Archivo | Qué es | Procedencia | sha256 (16 primeros) |
|---|---|---|---|
| `yolo26n-seg.pt` | YOLO26n-seg preentrenado en COCO (80 clases; vaca = 19). **Es el segmentador desplegado en el APK.** | Ultralytics, checkpoint fechado 2026-01-03, versión 8.3.222 | `361fbfabab285c32` |
| `yolo26n-seg.tflite` | Exportación LiteRT FP32 del anterior, `imgsz=640`, `end2end`. Idéntica byte a byte (cuerpo del modelo) a `app/assets/model_bundle/yolo26n-seg.tflite` y a `app-benchmark/assets/models/yolo26n_seg_fp32.tflite`. | `YOLO("yolo26n-seg.pt").export(format="litert", imgsz=640)`, ultralytics 8.4.128, 2026-08-25 12:31 | `14b35a7ba712f8b0` |
| `yolo26n-seg_w8a32.tflite` | Cuantización dinámica (pesos INT8). Falla en el runtime móvil; no se usa. | mismo export con `quantize="w8a32"`, 2026-08-25 | `ea6d2e0cfb79afca` |
| `yolo26n-seg-finetuned.pt` | Fine-tuning del 10 jun 2026 sobre el dataset viejo (builder del commit d2ca1d6, 614/176, 80 épocas, ultralytics 8.4.53). **Peor que el preentrenado sobre las máscaras manuales** (ver `informes/iou_val_manual_20260909/`). No desplegado. | entrenamiento local | `d6c65749431c100b` |
| `finetuned_20260610_d6c65749.pt` | Copia de seguridad del anterior con fecha y hash en el nombre. | copia 2026-09-09 | `d6c65749431c100b` |
| `yolo26n.pt` | YOLO26n de detección (cajas) para `capture.py` / `detect_live.py`. | Ultralytics | — |
| `weight_model.joblib` | RandomForest de peso, serializado con scikit-learn 1.8.0. Carga con avisos en 1.9. El APK no lo usa (usa `weight_model.json`, alométrico). | `train_weight_model.py`, 2026-06-09 | — |

El APK lleva además `app/assets/model_bundle/model_manifest.json` (sha256 del `.tflite` y de su cuerpo, `.pt` de origen y su
sha256, versiones de Ultralytics, `class_id` 19 = cow, 80 nombres, fecha de exportación). Lo genera
`src/make_model_manifest.py`; `config.ts` lee `class_id` de ahí y `estimarPeso.ts` guarda `peso:<versión>;seg:<sha256[0:16]>`
en `version_modelo` de cada estimación. `tests/test_export_contract.py` falla si el manifiesto no coincide con el archivo.

Reglas:
- `finetune_segmenter.py` escribe `finetuned_<AAAAMMDD>_<sha8>.pt` y nunca sobrescribe.
- Cualquier modelo que entre al APK debe pasar `tests/test_export_contract.py` y la paridad de área PC↔APK (≤1 %).
- Reproducir la exportación: `.venv/bin/python -c "from ultralytics import YOLO; YOLO('models/yolo26n-seg.pt').export(format='litert', imgsz=640)"`.
  El archivo resultante difiere solo en el zip `metadata.json` anexado (lleva la fecha); el cuerpo es idéntico.
