# Benchmark en dispositivo (Galaxy A25)

Aplicación Expo de un solo uso con la que se decidió, en agosto de 2026, si el pipeline de visión cabía en un teléfono
de gama media: inferencia LiteRT, lectura ArUco en JavaScript y paridad con el pipeline Python. No es la app de
producto; sus módulos de visión (`segment.ts`, `aruco.ts`, `tflite.ts`, `config.ts`, `image.ts`) pasaron a `app/`
sin cambios de algoritmo.

## Qué mide

- 10 fotos de campo empaquetadas (`assets/photos/`, con `manifest.json`), una vaca y el marcador ID 0 en cada una.
- Dos modelos: `yolo26n_seg_fp32.tflite` (12 MB) y `yolo26n_seg_w8a32.tflite` (3.5 MB, pesos INT8), copiados de
  `pipeline/models/`.
- Por foto y modelo, una corrida de calentamiento y cinco medidas; solo `runSync()` entra en el cronómetro. El
  postproceso de la máscara (`[1,32,160,160]`, recorte del letterbox, tamaño original) se registra aparte.
- ArUco una vez por foto sobre el RGBA a resolución fuente: tiempo, ID, esquinas y `cm_per_px = 15 / lado_px`.
- Arranque en frío: desde el primer módulo JS hasta la primera inferencia FP32, con la carga del modelo incluida.
- Criterio GO en pantalla: dispositivo `SM-A256*`, p50 de segmentación ≤ 2 500 ms, ArUco decodificado en al menos
  9 de 10, exportación del JSON sin error.

## Resultados (26 de agosto de 2026)

`informes/benchmark_a25_20260826.json` (ArUco reducido a 960 px) e `informes/benchmark_a25_20260826_fullres.json`
(ArUco a resolución fuente, esquema v2; lo usa `pipeline/tests/test_parity_a25.py`):

| Métrica | Resultado |
|---|---|
| Segmentación FP32, p50 / p95 | 456 / 470 ms (50 medidas) |
| w8a32 | falla en el primer `runSync()` del runtime móvil; el benchmark sigue con FP32 |
| ArUco a resolución fuente | 10 de 10 decodificadas, ≈ 1.4 s por foto; escala +0.63 % media frente a OpenCV subpíxel (a 960 px era +1.2 %) |
| Arranque en frío | 3.97 s |
| Paridad de área de segmentación con el pipeline | −0.24 % media, 0.72 % máximo (criterio ≤ 1 %) |

Veredicto GO: React Native + LiteRT FP32 + js-aruco2 cumple en el A25 y la app de producto se construyó sobre esta
base (`docs/03_arquitectura_apk.md`).

## Backend ArUco

`react-native-fast-opencv@1.0.1` no expone `aruco` ni `objdetect`, así que se usa `js-aruco2@2.0.0`: familia
`ARUCO_6X6_1000` limitada a los primeros 250 códigos (equivale a `DICT_6X6_250`), corrección de hasta 5 bits, solo
ID 0, esquinas a precisión de píxel (`subpixel_corners: false`). Por eso se detecta a resolución fuente: con
marcadores de 55–64 px en fotos de 1 280 px, ±1 px pesaba 1.2 % en la escala. En producción la cámara entrega
marcadores de 180–250 px.

## Cómo correr

```sh
cd app-benchmark
npm ci
npm run typecheck
npm run android            # JDK 17 + ANDROID_HOME + adb; compila, instala y arranca Metro en el A25 conectado
npm run start:dev-client   # Metro para un development client ya instalado
```

`react-native-fast-tflite` es un módulo nativo JSI: hace falta development client, no Expo Go. Para un APK con EAS en
local: `npx eas-cli build --platform android --profile development --local` con `JAVA_HOME` (JDK 17 con `javac`),
`ANDROID_HOME` y `EAS_LOCAL_BUILD_ARTIFACTS_DIR` exportados. En la app: esperar la medición de arranque en frío, pulsar
**Correr benchmark** y después **Exportar JSON**.

## El JSON (`schema_version: 2`)

- `device`: modelo, Android, ABI y memoria.
- `cold_start_ms`.
- `inference_runs[]`: `{ foto, modelo, phase (warmup | measured), run, ms }`. `summary.fp32` y `summary.w8a32` traen
  `p50_ms` y `p95_ms` (interpolación lineal) solo sobre `measured`; `model_failures` guarda el motivo si un modelo no corre.
- `aruco[]`: `{ foto, aruco_ms, decoded, marker_id, corners, marker_side_px, cm_per_px, aruco_working_resolution }`.
- `segmentation[]`: `{ foto, modelo, cow_dets, mask_area_px, cm_per_px, area_cm2, postprocess_ms }`;
  `area_cm2 = mask_area_px · cm_per_px²`.
- `configuration`: clase, umbrales, letterbox y backend ArUco, para la paridad con Python.

Para comparar con el pipeline: misma foto y modelo, `segmentation[].mask_area_px`, diferencia relativa ≤ 1 % con la
misma regla de selección (`pipeline/src/eval_segmenter_parity.py`).
