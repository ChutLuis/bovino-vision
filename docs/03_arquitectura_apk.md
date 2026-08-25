# Arquitectura del APK — Decisiones de diseño
**Correcciones atendidas: #9 (arquitectura/UML), #11 (flujo productivo), #12 (almacenamiento productivo)**
Estado: BORRADOR v0.1 — decisiones D1–D3 abiertas a debate

## Principio rector
Un solo APK (producto), dos flujos de datos separados:
- **Entrenamiento**: offline, en PC (`pipeline/`). El teléfono solo es cámara.
- **Productivo**: inferencia on-device en el teléfono. Nunca entrena, nunca requiere red.

Dispositivo de validación mínima: **Samsung Galaxy A25** (Exynos 1280, 6 GB RAM, sin GPU
dedicada aprovechable). Si cumple RNF-02 (≤ 3 s/foto) ahí, cumple en el parque real
de teléfonos del usuario objetivo.

## D1 — Formato de ejecución del modelo: **TFLite (LiteRT), FP16**

| Opción | Veredicto | Razón |
|---|---|---|
| **TFLite FP16** | **ELEGIDA** | Export directo desde Ultralytics (`model.export(format="tflite", half=True)`); runtime estándar de Android; delegates XNNPACK (CPU) disponibles en cualquier gama; YOLO26n-seg queda en ~6–12 MB |
| ONNX Runtime Mobile | Descartada | Viable, pero segundo ecosistema de dependencias sin ventaja clara en Android puro |
| ExecuTorch / PyTorch Mobile | Descartada | Menos maduro para despliegue Android de modelos Ultralytics |
| NCNN | Descartada | Excelente rendimiento pero toolchain de conversión más frágil; mantenimiento por una sola persona post-tesis |
| INT8 (cuantización entera) | Diferida | Ganancia de velocidad real, pero exige dataset de calibración y re-validar MAPE; solo si el A25 no cumple RNF-02 en FP16 |

**Riesgo controlado:** la exportación puede degradar la máscara → el plan de pruebas
incluye re-medir IoU y MAPE sobre el conjunto de campo CON el modelo TFLite (no el .pt),
en el teléfono. Es la verificación "probé la app, no solo el prototipo".

## D2 — Almacenamiento productivo: **SQLite (Room) + almacenamiento privado de la app**

- Base de datos: Room (SQLite) — tablas `animal` (arete, nombre, categoría) y
  `estimacion` (FK animal, peso_kg, intervalo, área_cm2, ruta_foto, timestamp, versión_modelo).
- Fotos: directorio privado de la app (`filesDir`), nombradas por timestamp; no MediaStore
  público (privacidad del hato = dato comercial del productor).
- Exportación: CSV por intent de compartir (RF-11).
- Sin nube, sin cuentas, sin telemetría → RNF-01/RNF-06 por construcción.
- `versión_modelo` en cada estimación: trazabilidad de qué modelo produjo qué peso
  (si el modelo se actualiza, el historial no miente).

## D3 — Stack de la app: **Kotlin + Jetpack Compose + CameraX + OpenCV Android**

- Kotlin/Compose: estándar actual de Android, UI declarativa rápida de iterar.
- CameraX: preview con análisis de frames para el feedback en vivo (RF-06/07).
- OpenCV Android SDK: módulo `aruco` (DICT_6X6_250) — mismo algoritmo que el pipeline
  Python; recorte del SDK para no reventar RNF-04 (≤ 80 MB).
- Mínimo Android 10 / API 29 (RNF-05).

## Componentes (base del diagrama de componentes, corr. 9)

```
app/
├── ui/            # Compose: CapturaScreen, ResultadoScreen, HistorialScreen, AnimalScreen
├── camera/        # CameraX: preview + análisis en vivo (marcador ✓ / animal ✓)
├── vision/
│   ├── Segmenter.kt        # TFLite: YOLO26n-seg → máscara       (≈ segmenter.py)
│   ├── ArucoScale.kt       # OpenCV: detección ArUco → cm/px     (≈ aruco.py + calibration.py)
│   └── Morphometry.kt      # área, longitud, altura desde máscara (≈ morphometry.py)
├── estimation/
│   └── WeightModel.kt      # W = a·A^b + intervalo de predicción (≈ train_weight_model.py, solo inferencia)
├── data/
│   ├── db/                 # Room: AnimalDao, EstimacionDao
│   └── export/             # CSV
└── domain/
    └── EstimarPesoUseCase.kt  # orquesta el flujo foto → peso
```

Cada clase de `vision/` y `estimation/` es espejo 1:1 de un módulo Python del
`pipeline/` — mismo algoritmo, otra plataforma. Ese mapeo es el argumento de
"el APK ES el prototipo validado, empacado".

## Flujo foto → peso (base del diagrama de secuencia, corr. 9)

1. `CapturaScreen` → CameraX entrega frame/foto.
2. `EstimarPesoUseCase` invoca `ArucoScale`: sin marcador legible → **rechazo con causa** (RF-07).
3. `Segmenter` (TFLite): sin vaca con confianza ≥ 0.5 → rechazo con causa.
4. `Morphometry`: máscara + escala cm/px → área lateral (cm²), longitud, altura.
5. `WeightModel`: área → peso ± intervalo (95%).
6. `ResultadoScreen`: peso + overlay de silueta sobre la foto (RF-06).
7. Usuario confirma animal (arete) → `EstimacionDao.insert()` → historial actualizado.

Tiempo objetivo total en A25: ≤ 3 s (RNF-02). Presupuesto estimado: segmentación
1.5–2.5 s (TFLite FP16 CPU), ArUco < 300 ms, resto despreciable.

## Fuera del APK (se queda en `pipeline/`, PC)
Anotación de máscaras, fine-tuning, ajuste alométrico, evaluaciones estadísticas,
generación de marcadores. El APK consume artefactos congelados: `model.tflite` +
coeficientes `{a, b}` + parámetros de intervalo, versionados juntos.
