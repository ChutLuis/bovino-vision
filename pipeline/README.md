# Prototipo — Estimación de peso bovino

Pipeline de captura para la tesis: detecta vacas Jersey adultas con YOLO26 + identifica al animal por marcador ArUco fijo en su collar, y dispara ráfagas de fotos sin operador presente.

## Hardware objetivo
- NVIDIA Jetson Orin Nano (despliegue en finca)
- Cámara USB (Logitech C270 HD recomendada)
- Marcadores ArUco DICT_6X6_250 impresos en PVC sintra de 12-15 cm

Durante desarrollo en macOS se usa la cámara integrada (FaceTime HD); la API de OpenCV es portable.

## Instalación

```bash
cd prototype
python3 -m pip install -r requirements.txt
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
prototype/
├── config.yaml          # parámetros tunables
├── JETSON_SETUP.md      # guía deploy en Jetson Orin Nano
├── src/
│   ├── generate_markers.py    # genera PDF imprimible
│   ├── detect_live.py         # visor debug
│   ├── capture.py             # pipeline autónoma
│   └── core/                  # módulos reutilizables
├── tests/
│   └── test_pipeline_smoke.py # E2E test (sin cámara)
├── data/
│   ├── markers/         # PDFs generados (gitignored)
│   └── captures/        # imágenes capturadas (gitignored)
└── models/              # pesos YOLO26 (gitignored)
```

## Estado actual

| Verificado en macOS | Por validar en Jetson |
|---|---|
| YOLO26n carga, detecta vaca conf 0.78-0.95 | PyTorch CUDA en ARM (ruedas NVIDIA) |
| ArUco roundtrip (gen → detect ID OK) | C270 USB index correcto |
| Smoke test E2E pasa | `cv2.imshow` con GUI de JetPack |
| Trigger/cooldown/storage | TensorRT FP16 export |

Ver **JETSON_SETUP.md** para el plan de deploy y troubleshooting.
