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

## D1 — Formato de ejecución del modelo: **LiteRT FP32** (decisión final)

**Evolución documentada:** v0.1 eligió "TFLite FP16" → la etapa 1 del spike reveló
que Ultralytics 8.4 ya no ofrece FP16 en LiteRT (opciones: FP32, INT8, w8a32) →
la etapa 2 mostró que w8a32 falla en el runtime móvil → **FP32 (12 MB) es la
decisión final**, validada en el A25 con margen 5.5× sobre el umbral de latencia.
La tabla siguiente conserva el análisis original (v0.1) como registro histórico:

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

### Resultados del spike — etapa 1: exportación y paridad (25 ago 2026, en PC)
**Corrección a D1:** Ultralytics 8.4 ya no soporta FP16 en LiteRT (nuevo nombre de
TFLite). Opciones reales: FP32, INT8 completo (requiere calibración) y **w8a32**
(cuantización dinámica: pesos INT8, activaciones FP32, **sin calibración**).

| Modelo | Tamaño | IoU vs .pt (35 fotos de campo, medio/mín) | Error de área vs .pt |
|---|---|---|---|
| yolo26n-seg.pt (referencia) | 5.9 MB | — | — |
| LiteRT FP32 | 12 MB | 0.985 / 0.971 | ~similar |
| **LiteRT w8a32** | **3.5 MB** | 0.983 / 0.971 | medio 0.71%, máx 2.55% |

Efecto en el peso del peor caso de área (2.55%): W ∝ A^0.706 → ~1.8% de sesgo,
dentro del presupuesto de error (MAPE 7.71%, umbral <10%). **Candidato principal:
w8a32** (3.5 MB, 4× más chico); el benchmark de velocidad en el A25 confirma.

Nota metodológica del propio spike: la primera medición dio IoU 0.70 por un error
de geometría en la comparación (la máscara LiteRT conserva el letterbox 640×640 y
la .pt no; redimensionar sin recortar el padding aplasta la silueta). Corregido el
recorte, la paridad real es 0.98. Lección idéntica a la de escala ArUco: primero
audita el instrumento de medición, después juzga al modelo.

### Resultados del spike — etapa 2: benchmark en dispositivo (26 ago 2026, Galaxy A25)
Corrida completa exportada (`benchmark_results.json`, app-benchmark): 10 fotos de
campo, 1 warmup + 5 corridas medidas por foto.

| Métrica | Resultado | Criterio | Veredicto |
|---|---|---|---|
| Segmentación FP32 (p50 / p95) | **449 / 466 ms** | ≤ 2,500 ms | **GO (margen 5.5×)** |
| Segmentación w8a32 | falla en primer `runSync()` | — | fallback FP32 pre-autorizado |
| ArUco (js-aruco2) decodificación | 10/10 | ≥ 9/10 | GO |
| ArUco paridad de escala vs OpenCV subpíxel | **+1.2% medio / +2.2% máx, sesgo sistemático** | ≤ 1% | **FALLA — en corrección** |
| Flujo total estimado (seg + ArUco + postproceso) | ~1.4 s | ≤ 3 s (RNF-02) | GO |

**Decisión D3 confirmada por evidencia:** React Native + LiteRT es viable en el
dispositivo objetivo. Referencia cruzada: el Jetson Orin Nano (GPU, 40 TOPS) hacía
el pipeline completo en 266 ms; un teléfono de gama media lo hace en ~1.4 s en CPU
— suficiente para captura foto-por-animal y argumento definitivo contra la
arquitectura cliente-servidor.

**w8a32:** el artefacto valida en el intérprete de escritorio (IoU 0.983 vs .pt)
pero falla en el runtime móvil (LiteRT 1.4.0 / react-native-fast-tflite 3.0.1).
Causa raíz no diagnosticada por decisión de alcance: FP32 (12 MB) cumple el
requerimiento con margen. Reabrir solo con: (1) prueba con `benchmark_model` CLI
oficial de LiteRT vía adb (discrimina librería vs wrapper), (2) instrumentación
del status de `TfLiteTensorCopyFromBuffer` en el wrapper, (3) identificación del
tensor 295.

**Paridad ArUco (`pipeline/src/eval_aruco_parity.py`):** js-aruco2 midió el marcador
sistemáticamente más chico que OpenCV subpíxel en las 10 fotos (mismo signo) →
escala +1.2%, área +2.4% media (máx +4.4%) → sesgo de peso ~+1.7%. Diagnóstico:
detección a 960 px con esquinas de precisión entera sobre un marcador de 55–64 px
(fotos WhatsApp de 1280 px). Dos mitigaciones en evaluación: (a) detectar a
resolución completa — en producción la cámara nativa da marcadores de 180–250 px,
donde ±1 px ≈ 0.5% de escala; (b) si no basta, refinamiento subpíxel propio o
módulo nativo OpenCV mínimo. **Principio documentado: coherencia instrumental** —
el modelo de peso se ajustó con áreas medidas por OpenCV; producción debe medir
con precisión equivalente o re-calibrar los coeficientes con el instrumento final.

**Paridad de área de segmentación A25 vs PC (misma selección, mayor área, conf 0.5):**
dif media −0.24%, |máx| 0.72%, sin sesgo sistemático → **PASA el criterio ≤1%**.
Con esto, la etapa de segmentación queda cerrada de punta a punta: el APK produce
las mismas áreas que el pipeline validado de la tesis. Sobre la resolución de
entrada: 640×640 no es una concesión del teléfono — es el punto de operación en
el que se validó TODO el sistema (el IoU 0.86 y el MAPE 7.71% de la tesis se
midieron con imgsz=640). Reentrenar/exportar a 960–1280 (≈4× píxeles, ≈4× latencia)
cambiaría de instrumento sin evidencia de necesidad. Único frente abierto del
spike: el sesgo de escala ArUco (experimento de resolución completa en curso).

### Resultados del spike — etapa 3: ArUco a resolución completa → **SPIKE CERRADO: GO**
(26 ago 2026, `informes/benchmark_a25_20260826_fullres.json`, schema v2)

Con detección sobre la imagen fuente (1280×960, sin reducción a 960):
- **Paridad de escala: PASA** — dif media +0.63%, máx 0.82% (antes: +1.2% / 2.2%).
- Costo: aruco_ms subió de ~830 a ~1,400 ms. Flujo total ≈ 2.0 s < 3 s (RNF-02 ✓).
- **Cold start medido: 3.97 s** (init JS → primera inferencia FP32, app recién
  abierta). Implicación de UX: pantalla de carga con precarga del modelo al abrir
  la app, no al tomar la foto.
- Sesgo residual sigue siendo sistemático (+0.63%, mismo signo: esquinas de
  precisión entera sin refinamiento subpíxel). Efecto en peso ≈ +0.9%, aceptable.
  En producción la cámara nativa da marcadores de 180–250 px (vs 55–64 px en
  estas fotos WhatsApp), donde el mismo error absoluto ≈ 0.15–0.2% de escala.
  Backlog opcional: refinamiento subpíxel propio si la validación de campo del
  APK muestra que el residual importa.

**Veredicto del spike completo:** React Native + LiteRT FP32 + js-aruco2 a
resolución completa cumple todos los criterios en el Galaxy A25. Se procede a
construir el APK de producto sobre esta base.

**Hallazgo de benchmark vs intuición:** el orden de rechazos asumido ("ArUco
barato primero") resultó invertido en el A25: segmentación 449 ms < ArUco 830 ms.
El orden definitivo del flujo se fija con los números de la iteración final.

## D2 — Almacenamiento productivo: **SQLite (Room) + almacenamiento privado de la app**

- Base de datos: Room (SQLite) — tablas `animal` (arete, nombre, categoría) y
  `estimacion` (FK animal, peso_kg, intervalo, área_cm2, ruta_foto, timestamp, versión_modelo).
- Fotos: directorio privado de la app (`filesDir`), nombradas por timestamp; no MediaStore
  público (privacidad del hato = dato comercial del productor).
- Exportación: CSV por intent de compartir (RF-11).
- Sin nube, sin cuentas, sin telemetría → RNF-01/RNF-06 por construcción.
- `versión_modelo` en cada estimación: trazabilidad de qué modelo produjo qué peso
  (si el modelo se actualiza, el historial no miente).

## D3 — Stack de la app: **React Native — CONFIRMADO por el spike (GO, 26 ago 2026)**

**Decisión revisada tras análisis (v0.2).** Criterios: el núcleo de inferencia
(TFLite) corre en C++ nativo vía JSI en ambos stacks → rendimiento del modelo
idéntico; la diferencia real es riesgo de calendario y propiedad del código.
El desarrollador domina React Native, no Kotlin: con RN escribe y defiende
~70% de la app él mismo; con Kotlin nativo defendería código ajeno (riesgo
tipo "mirroring"). La competencia del desarrollador es un factor de riesgo
de ingeniería legítimo (metodología, corr. 4).

- **UI/lógica:** React Native + react-native-vision-camera (captura y feedback en vivo).
- **Inferencia:** react-native-fast-tflite (JSI) con el modelo LiteRT FP32 de D1.
- **ArUco (único riesgo técnico del stack):** tres alternativas, decide el spike:
  1. `react-native-fast-opencv` (JSI) si expone el módulo aruco.
  2. Módulo nativo propio mínimo: solo `objdetect/aruco` de OpenCV, una función
     `detectarMarcador(foto) → esquinas`. Más trabajo, APK liviano.
  3. `js-aruco2` (JS puro, cero deps nativas) — solo si pasa la prueba de paridad.
- Mínimo Android 10 / API 29 (RNF-05).

### Spike de validación (1–2 días, en el Samsung A25)
Sale un veredicto GO/NO-GO de RN; si NO-GO, fallback a Kotlin (v0.1 de este doc).
1. App mínima RN + fast-tflite cargando `yolo26n-seg` FP16 → medir ms/inferencia
   sobre 5 fotos de campo reales. Umbral: segmentación ≤ 2.5 s.
2. Alternativa ArUco (en orden 1→2→3) decodificando ID 0 en 5 fotos de campo.
   Medir ms y tasa de decodificación.
3. **Prueba de paridad:** mismas 34 fotos por el pipeline Python y por RN —
   comparar factor cm/px y área (cm²). Criterio: diferencia ≤ 1%; si el área
   difiere más, la alternativa ArUco muere (el error de escala se propaga al
   cuadrado en el área y de ahí al peso).
4. Benchmark del orden de rechazos (RF-07): medir ArUco vs segmentación por
   separado; el barato-y-confiable se ejecuta primero.

## Componentes (base del diagrama de componentes, corr. 9)

```
app/ (React Native + Expo, TypeScript)
├── src/screens/       # CapturaScreen, ResultadoScreen, HistorialScreen, AnimalScreen
├── src/camera/        # react-native-vision-camera: preview + feedback en vivo (marcador ✓ / animal ✓)
├── src/vision/
│   ├── segmenter.ts       # react-native-fast-tflite (LiteRT FP32) → máscara   (≈ segmenter.py; validado en app-benchmark)
│   ├── arucoScale.ts      # js-aruco2 a resolución completa → cm/px            (≈ aruco.py + calibration.py; validado en app-benchmark)
│   └── morphometry.ts     # área, longitud, altura desde máscara               (≈ morphometry.py)
├── src/estimation/
│   └── weightModel.ts     # W = a·A^b + intervalo de predicción (coeficientes congelados; golden test en informes/)
├── src/data/
│   ├── db/                # expo-sqlite: animales, estimaciones (con versión_modelo)
│   └── export/            # CSV vía share intent
└── src/domain/
    └── estimarPeso.ts     # orquesta el flujo foto → peso (orden de rechazos medido)
```

Cada módulo de `src/vision/` y `src/estimation/` es espejo 1:1 de un módulo
Python del `pipeline/` — mismo algoritmo, otra plataforma — y los de visión ya
tienen implementación de referencia probada en `app-benchmark/src/`. Ese mapeo
es el argumento de "el APK ES el prototipo validado, empacado".
(La estructura Kotlin equivalente de v0.1 quedó descartada junto con D3-Kotlin.)

## Flujo foto → peso (base del diagrama de secuencia, corr. 9)

1. Pantalla de captura (react-native-vision-camera) entrega la foto.
2. `Segmenter` (LiteRT FP32): sin vaca con confianza ≥ 0.5 → **rechazo con causa** (RF-07).
3. `ArucoScale` (js-aruco2, resolución completa): sin marcador legible → rechazo con causa.
4. `Morphometry`: máscara + escala cm/px → área lateral (cm²), longitud, altura.
5. `WeightModel`: área → peso ± intervalo (95%).
6. Pantalla de resultado: peso + overlay de silueta sobre la foto (RF-06).
7. Usuario confirma animal (arete) → SQLite insert → historial actualizado.

**Orden de rechazos fijado por el benchmark** (no por intuición): la segmentación
(0.45 s) es más barata que ArUco (1.4 s) en el A25, así que se falla-rápido con
la vaca antes de pagar el marcador — inverso al supuesto original de v0.1.
Tiempo total medido en A25: **~2.0 s** ≤ 3 s (RNF-02 ✓); cold start 3.97 s →
precargar el modelo al abrir la app.

## Fuera del APK (se queda en `pipeline/`, PC)
Anotación de máscaras, fine-tuning, ajuste alométrico, evaluaciones estadísticas,
generación de marcadores. El APK consume artefactos congelados: `model.tflite` +
coeficientes `{a, b}` + parámetros de intervalo, versionados juntos.
