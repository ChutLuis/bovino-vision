# Wakx

Aplicación Android (React Native + Expo) que estima el peso vivo de una vaca a partir de una foto lateral con un
marcador ArUco de 15 cm. Funciona sin conexión: el modelo de segmentación y los coeficientes del modelo de peso
viajan dentro del APK.

## Flujo

1. Arranque: el modelo LiteRT se carga una sola vez (`ModelProvider`); la primera vez se muestran cuatro tarjetas de
   ayuda (`OnboardingScreen`).
2. Captura: foto con la cámara o desde la galería (`expo-image-picker`).
3. Procesando: segmentación, lectura del marcador a resolución fuente, área y peso. Se segmenta primero porque en el
   Galaxy A25 cuesta 0.45 s frente a 1.4 s del marcador: una foto sin vaca se rechaza antes de pagar lo caro.
4. Resultado: peso en grande, silueta pintada sobre la foto y recuadro del marcador; o un rechazo con la causa (sin vaca,
   sin marcador, marcador ilegible) y qué hacer.
5. Guardar: crea o actualiza el animal por arete, copia la foto al almacenamiento privado y escribe la estimación.
6. Historial: animales, sus pesadas, diferencia contra la anterior, tendencia y exportación a CSV.

## Estructura (`src/`)

| Ruta | Qué hace |
|---|---|
| `domain/estimarPeso.ts`, `domain/types.ts` | Orquesta foto → segmentación → marcador → área → peso; compone `version_modelo`. No toca UI ni base de datos. |
| `vision/` | `tflite.ts` (react-native-fast-tflite), `image.ts` (decodificación JPEG, orientación EXIF, letterbox 640×640), `segment.ts` (máscara y vaca de mayor área), `aruco.ts` (js-aruco2 a resolución fuente), `morphometry.ts` (área en cm²), `modelManifest.ts` y `config.ts` (clase y hash del segmentador leídos del manifiesto). |
| `estimation/` | `bundle.ts` carga `weight_model.json`; `weightModel.ts` aplica W = a·A^b. |
| `data/` | `db/schema.ts` y `db/dao.ts` (expo-sqlite), `photos.ts` (copia a `wakx-fotos/` privado), `export/csv.ts` (CSV e intent de compartir). |
| `providers/ModelProvider.tsx` | Precarga y calienta el modelo al abrir la app. |
| `screens/` | `SplashScreen`, `OnboardingScreen`, `CapturaScreen`, `ProcesandoScreen`, `ResultadoScreen`, `HistorialScreen`. |
| `ui/`, `navigation/` | `theme.ts`, `Botones.tsx`, `MarcaAruco.tsx`; stack tipado de React Navigation. |

## Paquete de modelo (`assets/model_bundle/`)

| Archivo | Contenido |
|---|---|
| `yolo26n-seg.tflite` | YOLO26n-seg preentrenado en COCO, LiteRT FP32, 12 MB; mismo cuerpo que `pipeline/models/yolo26n-seg.tflite`. |
| `model_manifest.json` | sha256 del `.tflite` y de su cuerpo, `.pt` de origen, versiones de Ultralytics, `class_id` 19 = cow, 80 nombres. Se valida al importar; `pipeline/tests/test_export_contract.py` falla si no coincide con el archivo. |
| `weight_model.json` | `a`, `b`, `interval`, `version`, `fuente`. Hoy `a = 0.375`, `b = 0.706`, `interval = null` (n = 34, laterales controladas); se reajusta con la campaña de calibración. |
| `golden_cases.json` | 10 casos área → peso con tolerancia 0.01 kg. |

Los coeficientes nunca se escriben en TypeScript. Cada estimación guarda
`version_modelo = peso:<versión>;seg:<sha256[0:16]>`, así el historial dice qué modelo produjo cada peso.

## Paridad con el benchmark

`segment.ts`, `aruco.ts`, `tflite.ts` y `config.ts` son los de `app-benchmark`, validados en el A25: NCHW 640, relleno
114/255, clase COCO 19, umbral 0.5, vaca de mayor área, máscara recortada al letterbox y ArUco a resolución fuente.
`image.ts` añade la decodificación de fotos externas y la normalización de la orientación EXIF antes del letterbox.
La app usa `run()` asíncrono en vez de `runSync()` para pintar cada etapa. En el dispositivo la foto golden da el área y
el peso esperados con desviación 0.00 % y de forma determinista (`informes/trazabilidad_a25_20260910/`); la ruta del
APK se reproduce en PC con `pipeline/src/core/segmenter_litert.py`.

## Comandos

```sh
cd app
npm ci
npm run typecheck              # tsc --noEmit
npm run test:golden            # compila weightModel.ts aislado y corre los 10 casos golden
npm run android -- SM_A256E    # busca un JDK 17, ANDROID_HOME y adb; compila, instala y arranca Metro en el dispositivo
npm run prebuild:android       # tras cambiar app.json o una dependencia nativa
npm run start:dev-client       # Metro para un development client ya instalado
```

`react-native-fast-tflite` es un módulo nativo JSI: hace falta un development client (`expo-dev-client`), no Expo Go.
El script de Android acepta `JDK_17_HOME` o `JAVA_HOME` para un JDK en ruta no estándar. Para un APK con EAS en
local: `npx eas-cli build --platform android --profile development --local` con `JAVA_HOME` (JDK 17 con `javac`),
`ANDROID_HOME` y `EAS_LOCAL_BUILD_ARTIFACTS_DIR` exportados; el perfil `development` está en `eas.json`.

## Base de datos

`animal(id, arete, nombre, categoria)` y `estimacion(id, animal_id, peso_kg, area_cm2, version_modelo, ruta_foto,
timestamp)` en `files/SQLite/wakx.db`, modo WAL. Para leerla por `adb` hay que copiar `wakx.db`, `wakx.db-wal` y
`wakx.db-shm` (`adb exec-out run-as com.luisc.wakx cat files/SQLite/wakx.db` y los dos hermanos); el `.db` solo son 4 KB.

El proyecto no fija `minSdkVersion`; rige el valor por defecto de la plantilla de Expo 57.
