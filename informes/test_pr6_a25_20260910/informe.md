# Informe de prueba en dispositivo — PR "Trazabilidad del segmentador en el APK"

Probado el 10 de septiembre de 2026 sobre `330cfe3`; fusionado en `master` como fast-forward
(mismo hash).

## Identificación

| Campo | Valor |
|---|---|
| Commit probado | `330cfe3` — *Trazabilidad del segmentador en el APK: manifiesto del modelo, clase desde el manifiesto y hash en cada estimación* |
| Rama | `trazabilidad-modelo-apk` (rebasada sobre `master` `a3c12f2`) |
| Fecha de la prueba | 10 de septiembre de 2026 |
| Teléfono | Samsung Galaxy A25 — `SM-A256E` (serial `R5CX90TFSYA`) |
| Android | 16 (API 36), build `BP4A.251205.006.A256EXXSDEZG2` |
| Build de la app | debug, dev-client, instalado con `npx expo run:android -d SM_A256E` |
| Paquete | `com.luisc.wakx` |

> **Nota metodológica sobre el APK probado.** Durante el paso 4 apareció un bug de la app que
> impedía escribir el arete completo (ver *Incidencia 1*). Se corrigió aparte y el
> APK reinstalado — con el que se ejecutaron los pasos 3 a 7 — incluye ese fix, que está **sin
> commitear** en el árbol de trabajo (`M app/src/screens/ResultadoScreen.tsx`). Ese fix **no toca
> ninguno de los cuatro ficheros del PR** ni la lógica de estimación o de guardado: se verificó que
> su diff no contiene ninguna línea con `version_modelo`, `area_cm2`, `peso`, `guardar`, `estimar`,
> `insert`, `db.` ni `sqlite`. La cadena que valida este PR
> (`model_manifest.json → modelManifest.ts → config.ts → estimarPeso.ts → SQLite → CSV`) es por
> tanto independiente de ese cambio y los resultados de abajo siguen siendo válidos para `330cfe3`.

## Qué se estaba validando

| Fichero del PR | Efecto esperado |
|---|---|
| `app/assets/model_bundle/model_manifest.json` | Ficha del `.tflite`: sha256 `14b35a7ba712f8b0…`, `class_id` 19, 80 nombres COCO |
| `app/src/vision/modelManifest.ts` | Carga y valida el manifiesto al importar; si el JSON estuviera mal, la app no arrancaría |
| `app/src/vision/config.ts` | `COW_COCO_CLASS` sale del manifiesto |
| `app/src/domain/estimarPeso.ts` | `version_modelo` pasa a `peso:2026-08-26-placeholder;seg:14b35a7ba712f8b0` |

## Resultados por paso

| Paso | Esperado | Observado | Estado | Captura |
|---|---|---|---|---|
| 0 · Entorno | Rama en `330cfe3`, adb autorizado | `330cfe3`; `R5CX90TFSYA device` | **OK** | — |
| 1 · Build e instalación | APK compila e instala | Instalado y ejecutándose. `npm run android` falla por selección interactiva de dispositivo; hay que usar `-d SM_A256E` | **OK** | — |
| 2 · Arranque | App arranca sin FATAL y llega a Captura | Proceso vivo, sin FATAL. Pantalla de Captura correcta ("Foto de lado.", "Tomar foto", "Elegir una foto de la galería"). El manifiesto valida en el import, luego la app arrancando ya prueba que el JSON es correcto | **OK** | `01_captura.png` |
| 3 · Foto golden | Área ≈ 15 138 cm² (±1 %), peso ≈ 335 kg (±3 kg) | **335 kg** en pantalla, "✓ Cuadro leído", máscara verde sobre la vaca correcta. En BD: área `15137.753795602774`, peso `335.08473412494067`. Golden: `15137.75` / `335.08` → coincidencia **exacta**, desviación 0.00 % | **OK** | `02_resultado_foto1.png` |
| 4 · Guardar + BD | Fila nueva con `version_modelo` compuesto | Fila `id=18`… ver salida literal abajo. `version_modelo = peso:2026-08-26-placeholder;seg:14b35a7ba712f8b0` | **OK** | — |
| 5 · Historial + CSV | Columna `version_modelo`: compuesta en las nuevas, vieja en las anteriores | Cabecera incluye `version_modelo`. Las 2 filas nuevas llevan el valor compuesto; las 14 anteriores conservan `2026-08-26-placeholder` (sin migración, esperado) | **OK** | — |
| 6 · Varias vacas | Debe seguir eligiendo la vaca de mayor área | Con 6 vacas en cuadro eligió la grande del primer plano; las 5 del fondo quedaron fuera de la máscara. "✓ Cuadro leído". Peso 174 kg (ver *Observación 3*) | **OK** | `03_resultado_multiple.png` |
| 7 · Repetibilidad | Área idéntica a la del paso 3 a la centésima | Área `15137.753795602774` en ambas corridas — idéntica en los 15 dígitos, no solo a la centésima. Peso idéntico también | **OK** | `04_resultado_repite.png` |

## Verificación de la cadena de trazabilidad

El hash que acaba en la base de datos se contrastó contra el binario real, no solo contra el manifiesto:

```
sha256 real del .tflite    14b35a7ba712f8b0fa7f95ac4aef00f42d2f8a017a72b5a6fabd4fdaff8f7d6d
sha256 en model_manifest   14b35a7ba712f8b0fa7f95ac4aef00f42d2f8a017a72b5a6fabd4fdaff8f7d6d
prefijo en version_modelo  14b35a7ba712f8b0
```

`class_id: 19` → `"19": "cow"` en el bloque `names` del manifiesto, con los 80 nombres COCO presentes.

## Salida literal de la consulta SQLite

Base extraída con `adb exec-out run-as com.luisc.wakx cat files/SQLite/wakx.db` más los ficheros
`-wal` y `-shm` (la base está en modo WAL: el `.db` suelto son solo 4096 bytes y los datos viven en
el `-wal` de 276 KB; copiar únicamente el `.db` habría dado una base vacía).

```
=== estimacion: ultimas 4 ===
(18, 10, 335.08473412494067, 15137.753795602774, 'peso:2026-08-26-placeholder;seg:14b35a7ba712f8b0', '2026-09-10T17:15:01.488Z')
(17, 9, 335.08473412494067, 15137.753795602774, 'peso:2026-08-26-placeholder;seg:14b35a7ba712f8b0', '2026-09-10T16:57:17.983Z')
(16, 6, 377.8898892109369, 17947.921879142043, '2026-08-26-placeholder', '2026-09-03T22:42:51.972Z')
(15, 2, 377.8898892109369, 17947.921879142043, '2026-08-26-placeholder', '2026-09-03T20:00:31.269Z')
```

Reparto sobre el total de la tabla:

```
=== reparto version_modelo ===
('2026-08-26-placeholder', 14)
('peso:2026-08-26-placeholder;seg:14b35a7ba712f8b0', 2)
```

Animales creados por la prueba:

```
=== animal id=9 ===
(9, '999901', None, None)
```

`id=17` es el paso 4 (arete 999901) y `id=18` el paso 7 (arete 999902, animal `id=10`).

## Líneas relevantes del CSV

Fichero exportado desde Historial → "Compartir historial (CSV)", copiado a
`wakx-historial.csv` (16 líneas: cabecera + 15 pesadas).

```csv
"arete","nombre","categoria","peso_kg","area_cm2","version_modelo","ruta_foto","timestamp"
"999902","","","335.08473412494067","15137.753795602774","peso:2026-08-26-placeholder;seg:14b35a7ba712f8b0","file:///data/user/0/com.luisc.wakx/files/wakx-fotos/estimacion-1789060501478.jpeg","2026-09-10T17:15:01.488Z"
"999901","","","335.08473412494067","15137.753795602774","peso:2026-08-26-placeholder;seg:14b35a7ba712f8b0","file:///data/user/0/com.luisc.wakx/files/wakx-fotos/estimacion-1789059437938.jpeg","2026-09-10T16:57:17.983Z"
"3698","","","377.8898892109369","17947.921879142043","2026-08-26-placeholder","file:///data/user/0/com.luisc.wakx/files/wakx-fotos/estimacion-1788475371962.jpeg","2026-09-03T22:42:51.972Z"
"12","","","377.8898892109369","17947.921879142043","2026-08-26-placeholder","file:///data/user/0/com.luisc.wakx/files/wakx-fotos/estimacion-1788465631256.jpeg","2026-09-03T20:00:31.269Z"
```

Convive el formato nuevo con el viejo en el mismo fichero sin romper el parseo ni desalinear
columnas, que era el punto a comprobar.

## Errores de logcat

### 1. `ClassNotFoundException` del splash screen — presente, atrapado, no bloqueante

Reproducible en cada arranque. Ya existía antes de este PR y no guarda relación con él.
La app se recupera y continúa: el proceso queda vivo y la UI se renderiza con normalidad.
Texto exacto:

```
09-10 11:16:15.823 E/DevLauncherController( 4337): Failed to hide splash screen
09-10 11:16:15.823 E/DevLauncherController( 4337): java.lang.ClassNotFoundException: expo.modules.splashscreen.SplashScreenManager
09-10 11:16:15.823 E/DevLauncherController( 4337): 	at java.lang.Class.classForName(Native Method)
09-10 11:16:15.823 E/DevLauncherController( 4337): 	at java.lang.Class.forName(Class.java:591)
09-10 11:16:15.823 E/DevLauncherController( 4337): 	at java.lang.Class.forName(Class.java:496)
09-10 11:16:15.823 E/DevLauncherController( 4337): 	at expo.modules.devlauncher.DevLauncherController$Companion.initialize$expo_dev_launcher_debug(DevLauncherController.kt:489)
09-10 11:16:15.823 E/DevLauncherController( 4337): 	at expo.modules.devlauncher.DevLauncherController$Companion.initialize(DevLauncherController.kt:527)
09-10 11:16:15.823 E/DevLauncherController( 4337): 	at expo.modules.devlauncher.DevLauncherController$Companion.initialize$default(DevLauncherController.kt:520)
09-10 11:16:15.823 E/DevLauncherController( 4337): 	at expo.modules.devlauncher.DevLauncherPackageDelegate$createApplicationLifecycleListeners$1.onCreate(DevLauncherPackageDelegate.kt:40)
09-10 11:16:15.823 E/DevLauncherController( 4337): 	at expo.modules.ApplicationLifecycleDispatcher.onApplicationCreate(ApplicationLifecycleDispatcher.kt:20)
09-10 11:16:15.823 E/DevLauncherController( 4337): 	at com.luisc.wakx.MainApplication.onCreate(MainApplication.kt:38)
09-10 11:16:15.823 E/DevLauncherController( 4337): 	at android.app.Instrumentation.callApplicationOnCreate(Instrumentation.java:1399)
09-10 11:16:15.823 E/DevLauncherController( 4337): 	at android.app.ActivityThread.handleBindApplication(ActivityThread.java:9125)
09-10 11:16:15.823 E/DevLauncherController( 4337): 	at android.app.ActivityThread.-$$Nest$mhandleBindApplication(ActivityThread.java:0)
09-10 11:16:15.823 E/DevLauncherController( 4337): 	at android.app.ActivityThread$H.handleMessage(ActivityThread.java:3016)
09-10 11:16:15.823 E/DevLauncherController( 4337): 	at android.os.Handler.dispatchMessage(Handler.java:132)
09-10 11:16:15.823 E/DevLauncherController( 4337): 	at android.os.Looper.dispatchMessage(Looper.java:358)
09-10 11:16:15.823 E/DevLauncherController( 4337): 	at android.os.Looper.loopOnce(Looper.java:288)
09-10 11:16:15.823 E/DevLauncherController( 4337): Caused by: java.lang.ClassNotFoundException: Didn't find class "expo.modules.splashscreen.SplashScreenManager" on path: DexPathList[[zip file "/data/app/~~lu1A9jAZ84jekLO_8qGFKg==/com.luisc.wakx-AT0cTzE6k1f7yENgvujgoQ==/base.apk"],nativeLibraryDirectories=[/data/app/~~lu1A9jAZ84jekLO_8qGFKg==/com.luisc.wakx-AT0cTzE6k1f7yENgvujgoQ==/lib/arm64, /data/app/~~lu1A9jAZ84jekLO_8qGFKg==/com.luisc.wakx-AT0cTzE6k1f7yENgvujgoQ==/base.apk!/lib/arm64-v8a, /system/lib64, /system/system_ext/lib64]]
```

### 2. Avisos menores, sin impacto

```
W/unknown:ReactNative( 3979): StatusBarModule: Ignored status bar change, current activity is edge-to-edge.
```

### 3. Cierres inesperados

**Ninguno.** No hay ni un `FATAL EXCEPTION` ni un `AndroidRuntime` de `com.luisc.wakx` en toda la
prueba. Las únicas líneas `AndroidRuntime` del log pertenecen al comando `monkey` usado para
relanzar la app. El proceso solo terminó cuando se le pidió explícitamente
(`am force-stop`, para capturar un arranque limpio). Tampoco se observó ningún ANR.

## Incidencias y observaciones

### Incidencia 1 — Bug del teclado al escribir el arete (encontrado aquí, ajeno al PR)

Al teclear el arete, el `TextInput` perdía el foco y cerraba el teclado a partir del 4.º dígito, y
después ya no admitía volver a enfocarse. No es un artefacto de adb: le ocurría igual al usuario con
el dedo. Medido con `adb shell dumpsys input_method` → `mInputShown=false` y con `uiautomator dump`
→ `focused="false"`.

Se investigó en paralelo y la causa raíz resultó ser el cambio en caliente de `elevation`/`shadow*`
en el contenedor del input enfocado (`campoEnfocado`): con el IME de Samsung en plena animación de
entrada provoca reinicio de sesión IME → `onFinishInput` → blur nativo → `closeCurrentInput`. El
desmontaje de los chips "Ya en el historial" (78 dp ≈ 220 px en este panel, medido en el volcado de
uiautomator: el botón "Guardar pesada" saltaba de `[45,1824][1035,1982]` a `[45,1604][1035,1762]`)
era la segunda puerta al mismo síntoma.

Ya está corregido en `app/src/screens/ResultadoScreen.tsx`, **sin commitear**. Verificado por mi
parte tras el fix: `adb shell input text "999901"` entra los 6 dígitos de un tirón conservando
`focused="true"` y `mInputShown=true`.

**No pertenece a este PR y debe gestionarse como cambio aparte.** Conviene decidir si entra como
PR propio antes o después de fusionar éste.

### Observación 2 — El selector de fotos de Android ordena por `datetaken`, no por fecha de copia

Al empujar fotos con `adb push` no aparecen arriba en el picker: `photo_01_camelia.jpeg` tiene
`datetaken=NULL` (se resolvió actualizando su `mtime`), pero `burst_taty_01.jpg` trae EXIF
`DateTime 2026:06:04 07:01:23` y quedaba enterrada en la sección de junio. `content update` sobre
`datetaken` es ignorado silenciosamente por MediaStore.

Se resolvió subiendo una copia sin el segmento APP1 (`burst_taty_01_noexif.jpg`). **La copia no está
recomprimida**: se eliminaron 75 428 bytes de metadatos conservando intacto el flujo comprimido, y
se comprobó que el sha256 del bitmap RGB decodificado es idéntico al del original
(`db9dd329d9ad5ba069f8279edc70bd298cb501831017c42b3d3c5f02b74a6bf3` en ambos), así que el resultado
de la segmentación no se ve afectado.

Es una peculiaridad del entorno de prueba, no un defecto de la app. Merece la pena anotarlo porque
condiciona cualquier automatización futura de esta prueba, y porque en el primer intento llevó a
seleccionar por error una foto distinta.

### Observación 3 — El peso de `burst_taty_01` (174 kg) parece bajo

La selección de animal es correcta —eligió la vaca de mayor área entre 6—, pero 174 kg queda por
debajo de lo plausible para ese ejemplar. La explicación más probable es de perspectiva: el patrón
ArUco está pegado a la pared en primer plano, muy por delante del animal, de modo que la escala
px→cm queda sesgada. Es una limitación del método de escalado, **ajena a este PR**, que no toca ni
la selección de animal ni la escala. Se anota por si interesa como caso de estudio para la
validación del ArUco.

## Ficheros generados

Todos en `informes/test_pr6_a25_20260910/` (sin commitear):

| Fichero | Contenido |
|---|---|
| `01_captura.png` | Pantalla de Captura tras el arranque |
| `02_resultado_foto1.png` | Resultado de `photo_01_camelia` — 335 kg |
| `03_resultado_multiple.png` | Resultado de `burst_taty_01` — 6 vacas, elige la mayor |
| `04_resultado_repite.png` | Repetición de `photo_01_camelia` — 335 kg |
| `wakx.db` | Copia de la base SQLite del dispositivo, ya consolidada (sqlite hizo checkpoint del WAL al abrirla, así que el fichero es autocontenido: 16 estimaciones) |
| `wakx-historial.csv` | CSV exportado desde el Historial |

## Veredicto

**Listo para fusionar** — la trazabilidad funciona de punta a punta (hash real del `.tflite` = manifiesto = `version_modelo` en SQLite y CSV), los valores golden salen exactos y deterministas, la selección de animal no ha cambiado, y la única incidencia encontrada (el teclado del arete) es ajena al PR y ya está corregida por separado.
