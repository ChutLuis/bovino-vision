# Pipeline (PC) — Estimación de peso bovino

Pipeline de investigación de la tesis (corre en PC): captura, anotación, segmentación, morfometría, modelo de peso, evaluaciones y exportación del modelo que consume el APK. Aquí ocurre todo el entrenamiento y la validación; el teléfono solo ejecuta artefactos congelados.

## Hardware objetivo
- NVIDIA Jetson Orin Nano (despliegue en finca)
- Cámara USB (Logitech C270 HD recomendada)
- Marcadores ArUco DICT_6X6_250 impresos en PVC sintra de 12-15 cm

Durante desarrollo en macOS se usa la cámara integrada (FaceTime HD); la API de OpenCV es portable.

## Instalación

```bash
cd pipeline
python3 -m pip install -r requirements.txt
# Versiones exactas con las que se validó el pipeline en PC (CPU): ver cabecera del archivo
python3 -m pip install -r requirements-lock.txt
python3 -m pytest -q          # pruebas (tests/)
```

## Uso

**1. Generar marcadores para imprimir:**
```bash
python3 src/generate_markers.py --ids 0-49 --size-cm 15 --out data/markers/markers.pdf
```

**2. Visor en vivo (para calibrar cámara, validar detección):**
```bash
python3 src/detect_live.py
```
Presiona `q` para salir.

**3. Captura autónoma (pipeline real):**
```bash
python3 src/capture.py --config config.yaml
```

## Estructura

```
pipeline/
├── config.yaml              # parámetros de captura
├── FINETUNING.md            # segmentador: split por animal, evaluación manual, veredicto
├── JETSON_SETUP.md          # guía de la Jetson (plataforma de validación del prototipo)
├── pytest.ini
├── src/
│   ├── core/                # aruco, calibration, segmenter (.pt), segmenter_litert (ruta del APK en PC), morphometry, seg_eval, ...
│   ├── capture.py, detect_live.py, generate_markers.py
│   ├── annotate_val.py      # anotación manual del conjunto de validación (MobileSAM + pincel)
│   ├── build_yolo_seg_dataset.py   # dataset YOLO-seg, split por animal sin fuga (--dry-run)
│   ├── finetune_segmenter.py       # entrenamiento (no sobrescribe pesos)
│   ├── eval_finetuned_iou.py       # IoU contra máscaras manuales, IC por animal, paneles (.pt o .tflite)
│   ├── eval_segmenter_parity.py    # .pt vs LiteRT-PC vs Galaxy A25 (paridad de área y decisión)
│   ├── measure_*.py, eval_weight_*.py, train_weight_model.py   # morfometría y modelo de peso
│   └── eval_aruco_parity.py        # paridad de escala móvil vs OpenCV
├── tests/                   # pytest: parseo de etiquetas, split, manifiesto, contrato LiteRT, emulador vs A25
├── data/
│   ├── field/               # datos de campo (ver data/field/README_DATASETS.md)
│   ├── field/seg_dataset/   # generado, gitignored
│   └── val_clean/           # 40 imágenes de validación anotadas a mano + manifest.csv
├── models/                  # pesos (gitignored); models/README.md lista procedencia y sha256
└── runs/                    # salidas de Ultralytics (gitignored)
```

Los crudos de campo (ráfagas `_grouped/`) viven fuera del repo en `Thesis_final_raw/` con `MANIFEST.sha1`;
los scripts los toman de `--raw`, `$BOVINO_RAW_GROUPED` o `~/Documents/Thesis_final_raw/raw/_grouped`.

## Estado actual

| Verificado en macOS | Por validar en Jetson |
|---|---|
| YOLO26n carga, detecta vaca conf 0.78-0.95 | PyTorch CUDA en ARM (ruedas NVIDIA) |
| ArUco roundtrip (gen → detect ID OK) | C270 USB index correcto |
| Smoke test E2E pasa | `cv2.imshow` con GUI de JetPack |
| Segmentador desplegado = YOLO26n-seg preentrenado (cls 19), LiteRT FP32 sha256 `14b35a7b…`, exportación reproducible (`tests/test_export_contract.py`) | — |
| Fine-tuning evaluado contra 40 máscaras manuales: empeora (ver FINETUNING.md) | — |
| Trigger/cooldown/storage | TensorRT FP16 export |

Ver **JETSON_SETUP.md** para el plan de deploy y troubleshooting.
