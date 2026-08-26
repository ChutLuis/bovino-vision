# Bovino Vision Benchmark

Spike Android para decidir GO/NO-GO del pipeline de vision de estimacion de peso bovino. No es una app de producto: usa 10 fotos de campo empaquetadas, ambos modelos LiteRT y registra cada medicion necesaria para contrastarla con el pipeline Python.

## Que mide

- `yolo26n_seg_fp32.tflite` y `yolo26n_seg_w8a32.tflite` se ejecutan por cada una de las 10 fotos.
- Cada foto/modelo tiene 1 corrida `warmup` y 5 corridas `measured`. Solo `TfliteModel.runSync()` queda dentro del cronometro de inferencia.
- Las detecciones de vaca son clase COCO `19` con confianza `>= 0.5`.
- La mascara se recompone desde `[1,32,160,160]`, se recorta el letterbox de 640x640 y solo despues se remuestrea con nearest-neighbor al tamano original. `mask_area_px` siempre esta en pixeles de la foto fuente. `postprocess_ms` se registra por separado y no se mezcla con la medicion de `runSync`.
- ArUco se corre una vez por foto sobre RGBA reescalado a un lado maximo de 960 px. Registra tiempo, ID 0, esquinas y lado del marcador.
- El archivo JSON contiene 120 ejecuciones de inferencia crudas: 10 fotos x 2 modelos x (1 warmup + 5 medidas).

## Backend ArUco

Se evaluo primero `react-native-fast-opencv@1.0.1`. El paquete publica un subconjunto de OpenCV y no expone `aruco`, `objdetect`, `ArucoDetector` ni `detectMarkers`; por eso no se instala en la app.

La app usa `js-aruco2@2.0.0` como fallback. El paquete contiene la familia OpenCV `ARUCO_6X6_1000`; el codigo limita sus primeros 250 codigos como `DICT_6X6_250`, usa el presupuesto de correccion de 5 bits de OpenCV, detecta solamente ID 0 y deja `subpixel_corners: false` porque esa biblioteca retorna esquinas a precision de pixel. Las diez fotos incluidas decodifican ID 0 tanto con el detector Python/OpenCV como con este backend JS antes de empaquetarlas.

El resultado GO/NO-GO de ArUco mide el backend JS que realmente queda en este spike, no una equivalencia implicita con OpenCV. El JSON identifica el backend y conserva las cuatro esquinas para que la prueba de paridad externa compare escala y orden de esquinas contra Python.

## Assets incluidos

Los modelos se copiaron desde:

- `../pipeline/models/yolo26n-seg.tflite` (FP32, 12 MB)
- `../pipeline/models/yolo26n-seg_w8a32.tflite` (w8a32, 3.5 MB)

Las 10 fotos estan en `assets/photos/`; sus nombres de origen e ID esperado estan en `assets/photos/manifest.json`. Son fotos con una vaca y el marcador ID 0 visible, seleccionadas de `../pipeline/data/field/*.jpeg`.

No hay llamadas de red, APIs ni telemetria en el flujo de benchmark. Los modelos, fotos y resultados permanecen en el dispositivo. Durante desarrollo, Expo Dev Client necesita el servidor Metro local para cargar JavaScript; eso no es una dependencia de red del pipeline ni de los assets incluidos.

El decodificador recibe solo estos assets canónicos de 1280x960, ya normalizados sin tag EXIF de orientacion. Esta herramienta no acepta capturas externas; cualquier reutilizacion para fotos de camara debe normalizar EXIF antes de llamar al preprocesamiento.

## Requisitos locales

- Node administrado por nvm.
- Android SDK y `adb` para instalacion por USB opcional.
- Cuenta/credenciales EAS ya configuradas para iniciar el build remoto.

Instalar dependencias:

```sh
cd "/home/luisc/Documents/bovino-vision/app-benchmark"
source ~/.nvm/nvm.sh && nvm use default
npm ci
```

Comprobar TypeScript y la integracion nativa antes de subir el build:

```sh
source ~/.nvm/nvm.sh && nvm use default
npm run typecheck
npx expo prebuild --platform android
```

## Build EAS de desarrollo

El perfil `development` genera un APK instalable con `expo-dev-client`; no funciona en Expo Go porque `react-native-fast-tflite` es un modulo nativo JSI.

```sh
cd "/home/luisc/Documents/bovino-vision/app-benchmark"
source ~/.nvm/nvm.sh && nvm use default
npx eas-cli@latest build --platform android --profile development
```

Si EAS solicita autenticacion o asociar el proyecto, el comando exacto previo es:

```sh
source ~/.nvm/nvm.sh && nvm use default
npx eas-cli@latest login
npx eas-cli@latest build:configure
```

No se debe inventar un resultado de este comando: requiere las credenciales de la cuenta EAS y el APK final se debe ejecutar en el Galaxy A25.

## Estado de verificacion de esta entrega

- TypeScript, prebuild Android y el bundle Android fueron validados localmente.
- No se inicio un build EAS ni se generaron tiempos: eso requiere la cuenta EAS configurada y ejecutar el APK en el Galaxy A25.
- La compilacion Gradle local requiere un Android SDK instalado. Si se desea hacerla fuera de EAS, configure una ruta real antes de ejecutar el wrapper:

```sh
export ANDROID_HOME="/ruta/al/Android/Sdk"
export PATH="$ANDROID_HOME/platform-tools:$ANDROID_HOME/cmdline-tools/latest/bin:$PATH"
cd "/home/luisc/Documents/bovino-vision/app-benchmark/android"
./gradlew :app:assembleDebug
```

La advertencia de `expo-doctor` sobre que `react-native-fast-tflite` no esta marcado en React Native Directory para New Architecture es metadata de ese directorio; el modulo es obligatorio para este spike y la comprobacion definitiva es el build EAS y la ejecucion en el A25.

## Instalar y ejecutar en el Galaxy A25

1. Descargue el enlace al APK que imprime EAS y habilite la instalacion desde esa fuente en el telefono, o instale por USB:

```sh
adb devices
adb install -r "/ruta/al/bovino-vision-benchmark.apk"
```

2. Desde la computadora, inicie Metro para el development client:

```sh
cd "/home/luisc/Documents/bovino-vision/app-benchmark"
source ~/.nvm/nvm.sh && nvm use default
npm run start:dev-client
```

3. Abra el development build en el A25, conectelo al servidor Metro local y pulse **Correr benchmark**. Al terminar, pulse **Exportar JSON** y elija una app o almacenamiento mediante el intent de compartir Android.

## Interpretar `benchmark_results.json`

`summary.fp32` y `summary.w8a32` contienen `p50_ms` y `p95_ms` calculados solo con registros `inference_runs` cuyo `phase` es `measured`. La definicion del percentil es interpolacion lineal sobre la muestra ordenada. Los registros `warmup` se exportan para trazabilidad pero no entran en los percentiles.

Campos principales:

- `device`: modelo, Android, ABI y memoria del telefono que produjo el resultado.
- `inference_runs`: cada `{ device, foto, modelo, phase, run, ms }` crudo.
- `aruco`: cada `{ foto, aruco_ms, decoded, marker_id, corners, marker_side_px }`. Las esquinas estan en coordenadas de la foto original, aunque la deteccion se hizo sobre la copia reescalada.
- `segmentation`: cada `{ foto, modelo, cow_dets, mask_area_px, postprocess_ms }`. La mascara seleccionada es la vaca de mayor area cuando hay mas de una deteccion; el tiempo de postproceso permite contrastar el presupuesto end-to-end sin contaminar los percentiles de inferencia.
- `configuration`: documenta clase COCO, umbrales, modelo de letterbox y backend ArUco para la prueba de paridad Python/RN.

Para comparar areas contra Python, use la misma foto y modelo. Compare `segmentation[].mask_area_px`; el criterio de paridad del spike es diferencia relativa `<= 1%` despues de aplicar la misma regla de seleccion de mascara.

## Criterio que muestra la app

La pantalla muestra `GO` solo cuando se cumplen todos los criterios:

1. El dispositivo identificado es un Samsung Galaxy A25 (`Galaxy A25` o `SM-A256*`).
2. `w8a32.p50_ms <= 2500` ms.
3. ArUco ID 0 se decodifica en al menos 9 de las 10 fotos.
4. `Exportar JSON` abre el intent de compartir sin error.

Si falla cualquiera, muestra `NO-GO` e identifica el criterio exacto. Antes de exportar, el resultado es necesariamente `NO-GO` provisional porque el cuarto criterio sigue pendiente.
