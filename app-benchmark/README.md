# Bovino Vision Benchmark

Spike Android para decidir GO/NO-GO del pipeline de vision de estimacion de peso bovino. No es una app de producto: usa 10 fotos de campo empaquetadas, ambos modelos LiteRT y registra cada medicion necesaria para contrastarla con el pipeline Python.

## Que mide

- `yolo26n_seg_fp32.tflite` y `yolo26n_seg_w8a32.tflite` se ejecutan por cada una de las 10 fotos.
- Cada foto/modelo tiene 1 corrida `warmup` y 5 corridas `measured`. Solo `TfliteModel.runSync()` queda dentro del cronometro de inferencia.
- Las detecciones de vaca son clase COCO `19` con confianza `>= 0.5`.
- La mascara se recompone desde `[1,32,160,160]`, se recorta el letterbox de 640x640 y solo despues se remuestrea con nearest-neighbor al tamano original. `mask_area_px` siempre esta en pixeles de la foto fuente. `postprocess_ms` se registra por separado y no se mezcla con la medicion de `runSync`.
- ArUco se corre una vez por foto sobre el RGBA fuente, sin reducir su lado maximo. Registra tiempo, ID 0, esquinas, resolucion efectiva y escala por foto.
- Al abrir la app, antes de habilitar el benchmark normal, se mide una inferencia FP32 en frio. `cold_start_ms` va desde la inicializacion del primer modulo JS hasta el retorno de esa primera inferencia e incluye la carga de FP32, decodificacion JPEG y letterbox.
- El archivo JSON conserva las ejecuciones crudas de cada modelo disponible: hasta 120 con ambos modelos (10 fotos x 2 modelos x 1 warmup + 5 medidas).

## Backend ArUco

Se evaluo primero `react-native-fast-opencv@1.0.1`. El paquete publica un subconjunto de OpenCV y no expone `aruco`, `objdetect`, `ArucoDetector` ni `detectMarkers`; por eso no se instala en la app.

La app usa `js-aruco2@2.0.0` como fallback. El paquete contiene la familia OpenCV `ARUCO_6X6_1000`; el codigo limita sus primeros 250 codigos como `DICT_6X6_250`, usa el presupuesto de correccion de 5 bits de OpenCV, detecta solamente ID 0 y deja `subpixel_corners: false` porque esa biblioteca retorna esquinas a precision de pixel. Las diez fotos incluidas decodifican ID 0 tanto con el detector Python/OpenCV como con este backend JS antes de empaquetarlas.

El refinamiento local subpixel queda pendiente de la paridad a resolucion fuente. No se introduce una correccion geometrica nueva antes de medir el efecto aislado de eliminar el reescalado a 960 px.

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

## Build EAS local

Para reproducir el perfil `development` en Linux sin subir un build, use `--local`. Requiere un **JDK 17 completo** (incluye `javac`), Android SDK y NDK; un JRE/Java 25 sin `javac` falla al configurar CMake con el mensaje `A restricted method in java.lang.System has been called`.

```sh
cd "/home/luisc/Documents/bovino-vision/app-benchmark"
source ~/.nvm/nvm.sh && nvm use default

export JAVA_HOME="/ruta/a/jdk-17"
export ANDROID_HOME="$HOME/Android/Sdk"
export ANDROID_SDK_ROOT="$ANDROID_HOME"
export PATH="$JAVA_HOME/bin:$ANDROID_HOME/platform-tools:$PATH"
export EAS_LOCAL_BUILD_ARTIFACTS_DIR="$PWD/build-artifacts"

java -version
javac -version
npx eas-cli@latest build --platform android --profile development --local
```

En Nobara/Fedora, el paquete de sistema correspondiente es normalmente `java-17-openjdk-devel`. El APK se escribe en `build-artifacts/`, que no se versiona.

## Flujo diario Android

Con el A25 conectado por USB, depuración USB autorizada y un JDK 17 instalado, el flujo normal crea/actualiza el development build, lo instala y arranca Metro:

```sh
cd "/home/luisc/Documents/bovino-vision/app-benchmark"
source ~/.nvm/nvm.sh && nvm use default
npm run android
```

El script busca un JDK 17 en `JDK_17_HOME`, `JAVA_HOME`, las rutas habituales de Nobara/Fedora y SDKMAN. Para una ruta no estándar:

```sh
export JDK_17_HOME="/ruta/a/jdk-17"
npm run android
```

Tras cambios en `app.json` o dependencias nativas, regenere primero el proyecto Android:

```sh
npm run prebuild:android
npm run android
```

## Estado de verificacion de esta entrega

- TypeScript, prebuild Android y el bundle Android fueron validados localmente.
- El perfil EAS local `development` compilo correctamente con JDK 17 y genero un APK. Aun no se instalaron ni midieron resultados en el Galaxy A25.
- La compilacion Gradle local requiere JDK 17 y un Android SDK instalado. Si se desea hacerla fuera de EAS, configure rutas reales antes de ejecutar el wrapper:

```sh
export ANDROID_HOME="/ruta/al/Android/Sdk"
export JAVA_HOME="/ruta/a/jdk-17"
export PATH="$JAVA_HOME/bin:$ANDROID_HOME/platform-tools:$PATH"
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

3. Mate el proceso de la app, abra el development build en el A25 y conectelo al servidor Metro local. Espere la medicion automatica de inicio en frio FP32 y despues pulse **Correr benchmark**. Al terminar, pulse **Exportar JSON** y elija una app o almacenamiento mediante el intent de compartir Android.

## Interpretar `benchmark_results.json`

El export usa `schema_version: 2`. `summary.fp32` y, cuando esta disponible, `summary.w8a32` contienen `p50_ms` y `p95_ms` calculados solo con registros `inference_runs` cuyo `phase` es `measured`. Si w8a32 falla durante `runSync()`, la prueba continua con FP32 y `summary.w8a32` es `null`; `model_failures.w8a32` conserva el motivo. La definicion del percentil es interpolacion lineal sobre la muestra ordenada. Los registros `warmup` se exportan para trazabilidad pero no entran en los percentiles.

Campos principales:

- `device`: modelo, Android, ABI y memoria del telefono que produjo el resultado.
- `cold_start_ms`: inicializacion JS de la app hasta el retorno de la primera inferencia FP32, con carga del modelo incluida. La medicion se inicia automaticamente para no incluir una pulsacion del usuario; no incluye el bootstrap nativo anterior al primer modulo JS.
- `inference_runs`: cada `{ device, foto, modelo, phase, run, ms }` crudo.
- `model_failures`: modelos no disponibles durante la corrida y el motivo reportado por el runtime.
- `aruco`: cada `{ foto, aruco_ms, decoded, marker_id, corners, marker_side_px, cm_per_px, aruco_working_resolution }`. `marker_side_px` es el promedio de los cuatro lados y `cm_per_px = 15 / marker_side_px`; las esquinas y la resolucion de trabajo estan en coordenadas fuente.
- `segmentation`: cada `{ foto, modelo, cow_dets, mask_area_px, cm_per_px, area_cm2, postprocess_ms }`. `area_cm2 = mask_area_px x cm_per_px^2`; queda en `null` si no se decodifico ArUco. La mascara seleccionada es la vaca de mayor area cuando hay mas de una deteccion; el tiempo de postproceso permite contrastar el presupuesto end-to-end sin contaminar los percentiles de inferencia.
- `configuration`: documenta clase COCO, umbrales, modelo de letterbox y backend ArUco para la prueba de paridad Python/RN.

Para comparar areas contra Python, use la misma foto y modelo. Compare `segmentation[].mask_area_px`; el criterio de paridad del spike es diferencia relativa `<= 1%` despues de aplicar la misma regla de seleccion de mascara.

## Criterio que muestra la app

La pantalla muestra `GO` solo cuando se cumplen todos los criterios:

1. El dispositivo identificado es un Samsung Galaxy A25 (`Galaxy A25` o `SM-A256*`).
2. `w8a32.p50_ms <= 2500` ms o, si w8a32 no puede ejecutar `runSync()`, `fp32.p50_ms <= 2500` ms. El JSON conserva el fallo de w8a32 en `model_failures`.
3. ArUco ID 0 se decodifica en al menos 9 de las 10 fotos.
4. `Exportar JSON` abre el intent de compartir sin error.

Si falla cualquiera, muestra `NO-GO` e identifica el criterio exacto. Antes de exportar, el resultado es necesariamente `NO-GO` provisional porque el cuarto criterio sigue pendiente.
