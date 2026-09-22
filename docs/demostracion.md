# Registro de demostración del flujo completo en el teléfono

Este documento registra una grabación de pantalla del funcionamiento de la aplicación Wakx en el
dispositivo de referencia, desde la selección de la fotografía hasta el historial.

## Condiciones de la grabación

| Campo | Valor |
|---|---|
| Fecha y hora | 21 de septiembre de 2026, 21:07 (hora del dispositivo: 9:06–9:07 p. m.) |
| Dispositivo | Samsung Galaxy A25 (SM-A256E), Android 16 |
| Paquete de instalación | `release_20260921_margen`, sha256 `4b524ea040f6b4bc11a0…` |
| `version_modelo` | `peso:campana-994d9c2cd1a6;seg:14b35a7ba712f8b0` |
| Archivo de video | `Screen_Recording_20260921_210757_Wakx.mp4` |
| Duración | 96.2 s |
| Resolución | 1080 × 2340 |
| Tamaño | 60 824 883 bytes |
| sha256 del video | `b080d0af462fa593298f1080a1e411061be0ab2a8a67a4e3781a7397bcf5a5b3` |

El archivo de video se conserva fuera del repositorio; su sha256 permite verificarlo.

## Recorrido observado

Las marcas de tiempo corresponden a la grabación. Los fotogramas enlazados están en
[`demostracion/`](demostracion/).

| Tiempo | Pantalla | Lo que se ve |
|---|---|---|
| 0–5 s | Inicio | Encabezado «Wakx» y «Historial». Título «Foto de lado.» bajo el rótulo «ANTES DE TOMAR LA FOTO», con los dos requisitos numerados: «Vaca completa — De cabeza a cola, de lado» y «Cuadro visible — Junto al costado, derecho y limpio». Imagen de ejemplo «Así debe verse» con la marca «Cuadro a 3–4 m». Botón «Tomar foto» y enlace «Elegir una foto de la galería» ([f01](demostracion/f01_inicio_04s.png)) |
| 6–9 s | Selector del sistema | Se abre la galería del teléfono y se elige una fotografía existente; la demostración usa la galería y no la cámara |
| 10–22 s | Revisando la foto | Rótulo «FOTO TOMADA» y título «Revisando la foto.», con la fotografía y el marcador visibles. Panel «PASO 1 DE 3 — Procesando la foto» y la lista «① Animal encontrado / ② Leyendo el cuadro… / ③ Calculando el peso», con el aviso «Esto tarda unos segundos. No cierre la aplicación» y el botón «Cancelar» ([f02](demostracion/f02_procesando_20s.png)) |
| 23–30 s | Revisando la foto | El panel avanza a «PASO 2 DE 3»: «Animal encontrado» queda marcado y «Leyendo el cuadro…» pasa a activo. Cerca de los 30 s alcanza «PASO 3 DE 3», con los dos primeros pasos marcados y «Calculando el peso» en curso |
| 31–34 s | Resultado | Miniatura con la silueta segmentada y la etiqueta «Cuadro leído». «PESO ESTIMADO 424 kg», «934 lb», «Margen ± 82 kg». Campo «ARETE DEL ANIMAL» («Escriba el arete», 1–6 dígitos), botón «Guardar pesada» inhabilitado con la leyenda «Escriba el arete para guardar», y «Repetir foto» ([f03](demostracion/f03_resultado_424_31s.png)) |
| 35–39 s | Foto con evidencia | Pantalla «Foto con evidencia — Máscara y cuadro detectados»: la fotografía con la máscara verde sobre el animal y la etiqueta «Cuadro leído» sobre el marcador. Al pie, «Máscara verde: animal detectado. Cuadro amarillo: referencia leída» ([f04](demostracion/f04_evidencia_36s.png)) |
| 40–44 s | Resultado | Se cierra la evidencia y se vuelve al resultado. Se escribe el arete con el teclado numérico |
| 45–46 s | Resultado | Con el arete «123» escrito, «Guardar pesada» se habilita y se pulsa |
| 47–50 s | Historial | Aviso «Pesada guardada · Arete 123 · 424 kg». Encabezado «Historial — 1 animal · 1 pesada» y la fila «Arete 1… Hoy, 9:07 p. m. — 424 kg, Primera pesada». Botones «Pesar otro animal» y «Compartir historial (CSV)» |
| 51–56 s | Inicio y selector | Se vuelve a la pantalla inicial y se abre de nuevo la galería para la segunda fotografía |
| 57–68 s | Revisando la foto | Segunda fotografía en proceso, «PASO 1 DE 3» |
| 69–76 s | Revisando la foto | El panel avanza a «PASO 2 DE 3» |
| 77–83 s | Resultado | «PESO ESTIMADO 389 kg», «858 lb», «Margen ± 74 kg». Bajo el campo de arete aparece «Ya en el historial (toque para usar):» con la ficha «123», que ofrece el arete ya registrado ([f05](demostracion/f05_resultado_389_77s.png)) |
| 81–82 s | Foto con evidencia | Se abre de nuevo la evidencia para la segunda fotografía: máscara verde y «Cuadro leído» |
| 84–86 s | Resultado | Se escribe el arete «223» y se pulsa «Guardar pesada»; el botón pasa a «Guardando…» |
| 87–93 s | Historial | Aviso «Pesada guardada · Arete 223 · 389 kg». Encabezado «Historial — 2 animales · 2 pesadas» con las filas «Arete 1… 424 kg» y «Arete 2… 389 kg», ambas «Primera pesada». Se abre el detalle de cada arete: «Arete 223 — 1 pesada, 389 kg» y «Arete 123 — 1 pesada, 424 kg», con la leyenda «Deslice una pesada a la izquierda para borrarla» y el botón «Compartir historial (CSV)» ([f06](demostracion/f06_historial_93s.png)) |
| 94–96 s | Inicio | Regreso a la pantalla inicial |

## Resultados registrados

| Orden | Peso | Equivalente | Margen | Arete de prueba |
|---|---|---|---|---|
| Primera fotografía | 424 kg | 934 lb | ± 82 kg | 123 |
| Segunda fotografía | 389 kg | 858 lb | ± 74 kg | 223 |

Los aretes 123 y 223 son identificadores de prueba introducidos durante la grabación; no corresponden a
los aretes de los animales.

Según el operador, las fotografías son de Estrellita y Esmeralda, en ese orden. No son las fotografías
primarias de esos animales: la estimación de la fotografía primaria de Estrellita es 417 kg (919 lb,
margen ± 81 kg), distinta de los 424 kg que muestra la grabación, de modo que la captura empleada aquí
es otra.

## Alcance de lo demostrado

La grabación muestra el flujo aceptado de extremo a extremo: selección de la fotografía, las tres etapas
del cálculo, el resultado con su margen, la pantalla de evidencia con la máscara y el marcador, el
guardado con arete y el historial con dos animales. El botón «Compartir historial (CSV)» aparece en
pantalla; la exportación no se ejecuta en la grabación.

La grabación no muestra el caso de rechazo: las tres condiciones que interrumpen el cálculo —ausencia de
animal detectado, marcador ausente o ilegible, y esquinas del marcador no recuperables— no aparecen en
este video. Su comportamiento se describe en la documentación de requerimientos y se implementa en
`app/src/domain/estimarPeso.ts`.
