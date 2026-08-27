# Wakx

APK offline para estimar peso bovino a partir de una foto lateral y un marcador
ArUco. Este directorio contiene el nucleo funcional y pantallas deliberadamente
sin estilo para que la capa de diseno pueda reemplazarse sin alterar la logica.

## Flujo

1. P0 carga el LiteRT FP32 una sola vez al abrir la app.
2. P1 toma una foto con la camara o la elige de la galeria.
3. P2 ejecuta, en este orden medido en el A25: segmentacion, ArUco a resolucion
   fuente y calculo de peso.
4. P3 muestra el peso o P3b muestra un rechazo explicable.
5. Guardar crea/actualiza el animal, copia la foto al almacenamiento privado y
   escribe la estimacion en SQLite.
6. P4 lista animales, sus estimaciones y comparte un CSV.

Se usa React Navigation con un native stack porque este flujo tiene pantallas y
retornos reales, y asi la navegacion queda separada de la logica de producto.

## Estructura

| Ruta | Responsabilidad |
| --- | --- |
| `src/domain/estimarPeso.ts` | Orquestador foto -> segmentacion -> ArUco -> area -> peso. No toca UI ni SQLite. |
| `src/vision/` | Paridad del benchmark: LiteRT FP32, letterbox, mascara, ArUco a resolucion completa y morfometria. |
| `src/estimation/weightModel.ts` | Lee los coeficientes del bundle y ejecuta el golden alometrico. |
| `src/data/db/` | Esquema SQLite y DAOs de `animal` y `estimacion`. |
| `src/data/photos.ts` | Copia la foto confirmada a `Paths.document/wakx-fotos/`, privado para la app. |
| `src/data/export/csv.ts` | Genera CSV y abre el share intent con `expo-sharing`. |
| `src/providers/ModelProvider.tsx` | Precarga y calienta el modelo en P0; nunca al tomar una foto. |
| `src/navigation/` | Stack tipado de React Navigation. |
| `src/camera/` | Reserva intencional para `react-native-vision-camera` y feedback en vivo de v1.1; v0 usa `expo-image-picker`. |

## Pantallas Para Diseno

| Pantalla | Componente | Props y logica que se deben conservar |
| --- | --- | --- |
| P0 Arranque | `src/screens/SplashScreen.tsx` | Observa `ModeloProvider`; no navegar a P1 hasta que el LiteRT este listo. |
| P1 Captura | `src/screens/CapturaScreen.tsx` | Devuelve `FotoEntrada` con URI y orientacion EXIF. La camara y galeria son v0. |
| P2 Procesando | `src/screens/ProcesandoScreen.tsx` | Muestra las etapas reales: `Buscando al animal…`, `Leyendo el marcador…`, `Calculando peso…`. |
| P3 Resultado | `src/screens/ResultadoScreen.tsx` | Recibe `ResultadoEstimacion` por ruta; conserva guardar animal/estimacion y repetir foto. |
| P3b Rechazo | `src/screens/ResultadoScreen.tsx` | Usa literalmente los mensajes de `MENSAJES_RECHAZO`. |
| P4 Historial | `src/screens/HistorialScreen.tsx` | Lista, detalle por animal y exportacion CSV. |

Los archivos de pantalla tienen marcas `TODO(diseno)`. No se agregaron librerias
de UI, estilos, tema ni componentes visuales reutilizables a proposito.

### Overlay De Resultado

`EstimacionExitosa` expone `mascara`, `esquinas_marcador`, `foto_uri` y el area.
En esta entrega `mascara.tipo` es `bbox_placeholder`: contiene el bbox de la
vaca y el area calculada, no un bitmap de mascara para dibujar. P3 no muestra
datos tecnicos al ganadero. Es una decision de timebox, no una mascara falsa;
el diseno puede montar primero foto + bbox + esquinas del marcador y reemplazarlo
por un renderer de silueta despues sin cambiar el resultado del dominio.

El bundle actual declara `"interval": null`; por eso P3 no inventa ni muestra
un intervalo de peso. Cuando el paquete congelado incluya un contrato de
intervalo definitivo, el renderer puede usar `intervalo_modelo`.

## Paridad Del Benchmark

Se preservan sin cambios de algoritmo `segment.ts`, `aruco.ts`, `tflite.ts` y
`config.ts` del benchmark validado. En `image.ts` solo se hicieron dos
adaptaciones aditivas necesarias para fotos externas:

- `decodeJpegUri()` aplica los mismos parametros de `jpeg-js` que la ruta de
  assets del benchmark.
- `normalizeExifOrientation()` normaliza la imagen antes del letterbox. El
  benchmark recibia JPEG canonicos sin orientacion EXIF; una foto de camara no
  puede omitir esa normalizacion sin cambiar el instrumento de medicion.

No se cambiaron NCHW 640, padding 114/255, clase COCO 19, umbral 0.5, seleccion
por mayor area, reconstruccion/crop de mascara ni ArUco de resolucion fuente.
El orquestador falla primero por `sin_vaca`, antes de pagar el costo de ArUco,
tal como exige la medicion del Galaxy A25.

El benchmark usa `runSync()` para medir solo la inferencia. Producto usa la API
asincrona `run()` con los mismos input y tensores de salida, para que P2 pueda
pintar cada mensaje antes de la etapa costosa; esta adaptacion de scheduling no
cambia el algoritmo ni los artefactos y queda pendiente de validar en el A25.

`jpeg-js` procesa JPEG. La captura Android esperada entrega JPEG; al probar la
galeria en dispositivo, use una foto JPEG. Soporte para otros formatos no se
declara hasta validarlo con una conversion que preserve la geometria.

## Bundle Congelado

`assets/model_bundle/` es el contrato entre el pipeline de PC y el APK:

```text
yolo26n-seg.tflite
weight_model.json
golden_cases.json
```

Los coeficientes alometricos no aparecen escritos en TypeScript. Se cargan de
`weight_model.json`, y `version_modelo` se guarda con cada fila de SQLite.

## Comprobaciones Locales

El proyecto no tiene `.nvmrc`; use el default configurado por nvm:

```sh
cd "/home/luisc/Documents/bovino-vision/app"
source ~/.nvm/nvm.sh && nvm use default
npm ci
npm run typecheck
npm run test:golden
```

`npm run test:golden` compila de forma aislada `weightModel.ts`, ejecuta los 10
casos de `golden_cases.json` y exige `|peso - esperado| <= 0.01 kg`. El directorio
temporal `.golden-build/` esta ignorado por Git.

Para arrancar Metro con un development client ya instalado:

```sh
source ~/.nvm/nvm.sh && nvm use default
npx expo start --dev-client
```

No use Expo Go: `react-native-fast-tflite` es un modulo nativo JSI y requiere
el development client.

## Debug Rapido En El A25

Wakx replica el comando de desarrollo de `app-benchmark`. Con el A25 conectado
por USB y la depuracion autorizada, el comando busca un JDK 17 completo,
configura `ANDROID_HOME` y ejecuta `expo run:android --device` para compilar o
actualizar el development client, instalarlo y arrancar Metro:

```sh
cd "/home/luisc/Documents/bovino-vision/app"
source ~/.nvm/nvm.sh && nvm use default
npm run android
```

Para una instalacion de JDK no estandar:

```sh
export JDK_17_HOME="/ruta/a/jdk-17"
npm run android
```

Despues de cambiar `app.json` o una dependencia nativa, sincronice el proyecto
Android generado y vuelva a ejecutar el mismo comando:

```sh
source ~/.nvm/nvm.sh && nvm use default
npm run prebuild:android
npm run android
```

## Build EAS Local Para El A25

Requiere JDK 17 completo con `javac`, Android SDK, NDK y un dispositivo con
depuracion USB autorizada. El benchmark ya verifico que esta maquina necesita
JDK 17, no un JRE ni Java 25.

```sh
cd "/home/luisc/Documents/bovino-vision/app"
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

Si EAS pide autenticar o asociar el proyecto por primera vez, ejecute antes:

```sh
source ~/.nvm/nvm.sh && nvm use default
npx eas-cli@latest login
npx eas-cli@latest build:configure
```

El perfil `development` ya esta en `eas.json` y coincide con el benchmark. No
se copia el `projectId` de aquel: `build:configure` debe crear o asociar el
proyecto EAS propio de Wakx (`com.luisc.wakx`).

El perfil `development` de `eas.json` genera un APK interno. Instalelo y arranque
Metro asi:

```sh
adb devices
adb install -r "/ruta/a/build-artifacts/wakx.apk"
source ~/.nvm/nvm.sh && nvm use default
npx expo start --dev-client
```

Despues de cambios a `app.json` o dependencias nativas, regenere antes de volver
a construir:

```sh
source ~/.nvm/nvm.sh && nvm use default
npx expo prebuild --platform android
```

## Validacion Pendiente En Dispositivo

El typecheck y el golden alometrico se ejecutan localmente sin telefono. La
inferencia LiteRT, la lectura ArUco, permisos de camara/galeria, copia privada
de fotos, SQLite y el share intent necesitan esta corrida real en el A25:

```sh
cd "/home/luisc/Documents/bovino-vision/app"
source ~/.nvm/nvm.sh && nvm use default
npm run typecheck
npm run test:golden
npx eas-cli@latest build --platform android --profile development --local
adb install -r "/ruta/al/APK-generado.apk"
npx expo start --dev-client
```

No se afirma aqui un resultado de esa corrida hasta ejecutarla en el dispositivo.
