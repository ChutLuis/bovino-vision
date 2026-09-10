# Trazabilidad del segmentador probada en el Galaxy A25 — 10 de septiembre de 2026

Prueba en dispositivo de la cadena que identifica el segmentador en cada estimación:
`model_manifest.json` → `modelManifest.ts` → `config.ts` → `estimarPeso.ts` → SQLite → CSV.

| Campo | Valor |
|---|---|
| Teléfono | Samsung Galaxy A25, `SM-A256E`, Android 16 (API 36), build `BP4A.251205.006.A256EXXSDEZG2` |
| Build de la app | debug con dev-client, instalado con `npx expo run:android -d SM_A256E`; paquete `com.luisc.wakx` |
| Qué se valida | `app/assets/model_bundle/model_manifest.json` (sha256 del `.tflite`, `class_id` 19, 80 nombres COCO); `modelManifest.ts` valida el JSON al importar; `config.ts` toma `COW_COCO_CLASS` del manifiesto; `estimarPeso.ts` guarda `version_modelo = peso:<versión>;seg:<sha256[0:16]>` |

## Resultados

| Paso | Esperado | Observado | Captura |
|---|---|---|---|
| Arranque | Sin `FATAL`, llega a Captura | Proceso vivo; pantalla de Captura correcta. Como el manifiesto se valida en el import, arrancar ya prueba que el JSON es válido | `01_captura.png` |
| Foto golden (`photo_01_camelia`) | Área ≈ 15 138 cm² (±1 %), peso ≈ 335 kg (±3 kg) | 335 kg en pantalla, máscara sobre la vaca correcta. En la base: área `15137.753795602774`, peso `335.08473412494067`; el golden espera `15137.75` / `335.08` (desviación 0.00 %) | `02_resultado_foto1.png` |
| Guardar | Fila nueva con `version_modelo` compuesto | `peso:2026-08-26-placeholder;seg:14b35a7ba712f8b0` | — |
| Historial y CSV | Columna `version_modelo` con el formato nuevo en las filas nuevas y el viejo en las anteriores | Cabecera con `version_modelo`; 2 filas nuevas con el valor compuesto, 14 anteriores con `2026-08-26-placeholder`; el CSV no se desalinea | — |
| Varias vacas (`burst_taty_01`, 6 en cuadro) | Elige la de mayor área | Eligió la del primer plano; las 5 del fondo fuera de la máscara. Peso 174 kg (ver observación 3) | `03_resultado_multiple.png` |
| Repetibilidad | Misma área que la foto golden | Área idéntica en los 15 dígitos y mismo peso en dos corridas | `04_resultado_repite.png` |

Cadena de hashes, contrastada contra el binario y no solo contra el manifiesto:

```
sha256 real del .tflite    14b35a7ba712f8b0fa7f95ac4aef00f42d2f8a017a72b5a6fabd4fdaff8f7d6d
sha256 en model_manifest   14b35a7ba712f8b0fa7f95ac4aef00f42d2f8a017a72b5a6fabd4fdaff8f7d6d
prefijo en version_modelo  14b35a7ba712f8b0
```

`class_id: 19` resuelve a `"cow"` en el bloque `names` del manifiesto.

## Base de datos y CSV

La base del dispositivo está en modo WAL: el `.db` suelto son 4096 bytes y los datos viven en el `-wal` (276 KB).
Para leerla por `adb` hay que copiar `.db`, `-wal` y `-shm` (`adb exec-out run-as com.luisc.wakx cat files/SQLite/wakx.db`
y los dos ficheros hermanos). Últimas cuatro estimaciones y reparto de `version_modelo`:

```
(18, 10, 335.08473412494067, 15137.753795602774, 'peso:2026-08-26-placeholder;seg:14b35a7ba712f8b0', '2026-09-10T17:15:01.488Z')
(17, 9,  335.08473412494067, 15137.753795602774, 'peso:2026-08-26-placeholder;seg:14b35a7ba712f8b0', '2026-09-10T16:57:17.983Z')
(16, 6,  377.8898892109369,  17947.921879142043, '2026-08-26-placeholder', '2026-09-03T22:42:51.972Z')
(15, 2,  377.8898892109369,  17947.921879142043, '2026-08-26-placeholder', '2026-09-03T20:00:31.269Z')

('2026-08-26-placeholder', 14)
('peso:2026-08-26-placeholder;seg:14b35a7ba712f8b0', 2)
```

CSV exportado desde Historial → "Compartir historial (CSV)" (`wakx-historial.csv`, cabecera + 15 pesadas), primeras filas:

```csv
"arete","nombre","categoria","peso_kg","area_cm2","version_modelo","ruta_foto","timestamp"
"999902","","","335.08473412494067","15137.753795602774","peso:2026-08-26-placeholder;seg:14b35a7ba712f8b0","file:///data/user/0/com.luisc.wakx/files/wakx-fotos/estimacion-1789060501478.jpeg","2026-09-10T17:15:01.488Z"
"3698","","","377.8898892109369","17947.921879142043","2026-08-26-placeholder","file:///data/user/0/com.luisc.wakx/files/wakx-fotos/estimacion-1788475371962.jpeg","2026-09-03T22:42:51.972Z"
```

## Logcat

- `java.lang.ClassNotFoundException: expo.modules.splashscreen.SplashScreenManager` desde `DevLauncherController`
  ("Failed to hide splash screen") en cada arranque. Lo lanza el dev-launcher porque `expo-splash-screen` no está en
  `package.json`; queda atrapado y la app continúa. Un build release sin dev-client no pasa por ese código.
- `StatusBarModule: Ignored status bar change, current activity is edge-to-edge` (aviso, sin efecto).
- Ningún `FATAL EXCEPTION`, ningún `AndroidRuntime` de `com.luisc.wakx`, ningún ANR. El proceso solo terminó con `am force-stop`.

## Observaciones

1. **Campo de arete y teclado de Samsung.** Al teclear el arete, el `TextInput` perdía el foco a partir del 4.º dígito y
   no admitía volver a enfocarse (también con el dedo; `dumpsys input_method` → `mInputShown=false`). Causa: el cambio en
   caliente de `elevation`/`shadow*` del contenedor enfocado durante la animación de entrada del IME reinicia la sesión
   IME → `onFinishInput` → blur nativo; el desmontaje de los chips "Ya en el historial" (≈ 220 px) era la segunda vía al
   mismo síntoma. Corregido en `app/src/screens/ResultadoScreen.tsx` (contenedor estable, altura real del teclado para
   el relleno inferior, `keyboardShouldPersistTaps="always"`). Verificado: `adb shell input text "999901"` entra los 6
   dígitos conservando `focused="true"` y `mInputShown=true`.
2. **El selector de fotos ordena por `datetaken` (EXIF), no por fecha de copia.** Una foto de junio empujada con
   `adb push` queda enterrada en su mes, y `content update` sobre `datetaken` se ignora. Copiar la foto sin el segmento
   APP1 la sube arriba sin alterar los píxeles (sha256 del bitmap RGB decodificado idéntico:
   `db9dd329d9ad5ba069f8279edc70bd298cb501831017c42b3d3c5f02b74a6bf3`). Solo es seguro si `Orientation` es 1 o no
   existe, porque la app normaliza la orientación EXIF antes de segmentar (`app/src/vision/image.ts`).
3. **El peso de `burst_taty_01` (174 kg) es un sesgo de escala, no de selección.** La selección fue correcta (mayor área
   entre 6, IoU 0.87 con la máscara manual). El marcador está pegado a la pared en primer plano, más cerca de la cámara
   que el animal, y la escala px→cm hereda esa distancia:

   | Dato | Valor |
   |---|---|
   | Lado del marcador en `burst_taty_01` | 155 px (mediana de las 40 imágenes manuales: 89 px; máximo 176) |
   | Área con la máscara manual y marcador de 15 cm | 5 108 cm² |
   | Área que implica 174 kg con `weight_model.json` (0.375·A^0.706) | ≈ 5 980 cm² |
   | `lateral_area_cm2` mediana en las ráfagas de junio (`features_grouped.csv`, 497 fotos, 19 vacas) | 9 209 cm² |
   | Área de Camelia (335 kg) en el golden | 15 138 cm² |
   | Fotos de las 40 manuales con el marcador fuera de la caja de la vaca objetivo (`informes/seleccion_vaca_20260910/por_imagen.csv`) | 37 de 40 |

   Con el marcador 1.7× más cerca que el animal el área en cm² se divide por ≈ 3 y el peso cae. El pipeline en PC da
   lo mismo que la app, así que no es defecto del APK sino del protocolo de captura de junio (marcador en poste o
   pared). Por eso el protocolo de la campaña de calibración lleva el marcador al costado del animal
   (`docs/02_protocolo_campo.md`).

## Archivos

| Fichero | Contenido |
|---|---|
| `01_captura.png` | Pantalla de Captura tras el arranque |
| `02_resultado_foto1.png` | Resultado de `photo_01_camelia`: 335 kg |
| `03_resultado_multiple.png` | Resultado de `burst_taty_01`: 6 vacas, elige la mayor |
| `04_resultado_repite.png` | Repetición de `photo_01_camelia`: 335 kg |
| `wakx.db` | Copia consolidada de la base SQLite del dispositivo (16 estimaciones) |
| `wakx-historial.csv` | CSV exportado desde el Historial |

## Conclusión

La trazabilidad funciona de punta a punta: el hash real del `.tflite` coincide con el manifiesto y con `version_modelo`
en SQLite y en el CSV; los valores golden salen exactos y deterministas; la selección de animal no cambió; las filas
antiguas conviven con las nuevas sin migración.
