# Latencia del flujo de estimación en la compilación de entrega — Galaxy A25, 19 de septiembre de 2026

Tiempo por fotografía del flujo completo de Wakx (lectura, decodificación JPEG, orientación EXIF, letterbox, tensor,
inferencia LiteRT, postproceso, ArUco, área y peso) en una compilación Android de lanzamiento (Hermes, sin modo de
desarrollo, CPU, sin red), sobre seis fotografías originales de 12 MP de la campaña del 12 de septiembre de 2026
empaquetadas dentro de un APK de prueba con identidad separada (`com.luisc.wakx.benchmark`, sha256 `bd3b01fbf05bfcb9…`).
El código de visión, dominio y paquete es el del producto byte a byte; el segmentador es el desplegado
(`14b35a7ba712f8b0…`). Galaxy A25 SM-A256E, Android 16 (API 36), arm64-v8a, batería al 100 % y conectada por USB.

Dos modos sobre las mismas fotografías: **A**, `estimarPeso` del producto sin alterar (solo el tiempo total); **B**, las
mismas funciones con marcas de tiempo entre etapas. Dos baterías de 66 corridas cada una: una de acondicionamiento y
cinco medidas por fotografía y modo, con el orden de las fotografías barajado con semilla fija. La batería 2 se ejecutó
en estado térmico estacionario y es la que se reporta; `bench_bateria2_20260919_0855.csv` contiene sus 66 corridas con
el tiempo de cada etapa, el resultado (aceptada o rechazo con causa), la máscara, la escala, el área y el peso. Tres
arranques de proceso adicionales midieron la primera estimación tras arrancar.

## Mediana de cinco repeticiones por fotografía (ms, batería 2)

| Fotografía | Resultado | Total modo A | Total modo B | JPEG | Letterbox | Inferencia | Postproceso | ArUco |
|---|---|---|---|---|---|---|---|---|
| `IMG_20260912_065052` | aceptada | 25 535 | 25 568 | 13 731 | 244 | 564 | 386 | 10 592 |
| `IMG_20260912_073927_2` | aceptada | 26 960 | 26 950 | 14 851 | 243 | 529 | 519 | 10 742 |
| `IMG_20260912_071121` | aceptada | 29 087 | 28 913 | 15 194 | 244 | 547 | 344 | 12 566 |
| `IMG_20260912_070836` | rechazo sin animal | 15 894 | 15 828 | 14 962 | 244 | 553 | 0.2 | no se ejecuta |
| `IMG_20260912_080328` | rechazo sin animal | 15 995 | 15 921 | 15 095 | 244 | 530 | 0.2 | no se ejecuta |
| `20260912_080628` | rechazo sin animal | 13 179 | 13 187 | 12 317 | 246 | 579 | 0.2 | no se ejecuta |

Las etapas que el flujo no ejecuta se marcan así y no como 0 ms: el rechazo temprano por `sin_vaca` se conserva y en esos
casos nunca se llama a ArUco. `exif` es 0.0 ms porque las seis fotografías tienen orientación 0 o 1 y la rama de rotación
no se ejercitó; `lectura`, `buffer`, `área` y `peso` están por debajo de 45 ms.

Reparto agregado en estado estacionario (modo B): en fotografías aceptadas la mediana del total es 26.8 s, con JPEG
14.7 s (55 %), ArUco 10.7 s (40 %), inferencia 0.55 s (2 %), postproceso 0.39 s (1.4 %) y letterbox 0.24 s (0.9 %); en
rechazos sin animal, 15.5 s, con JPEG al 95 % porque el rechazo temprano evita ArUco. La suma de etapas cubre el 99.5 %
del total: no hay tiempo escondido entre marcas. El postproceso incluye la construcción del overlay de la máscara,
que es postproceso real del producto.

## Arranque y calentamiento

La primera estimación tras arrancar el proceso fue de 20.6 s (tres arranques, misma fotografía) frente a 27.0 s de esa
fotografía en estado estacionario. La temperatura de la batería subió de 33.2 a 37.8 °C a lo largo de las dos baterías y
el rendimiento se degradó de forma monótona hasta estabilizarse; las corridas lentas no se descartaron. El arranque de
proceso tarda 249–294 ms, la carga del modelo 60–102 ms y el calentamiento del proveedor 501–652 ms, una sola vez.

## Paridad

`paridad.csv`: en las dos baterías, cada fotografía dio la misma selección de vaca, la misma área en píxeles y el mismo
peso en las diez corridas (modos A y B idénticos), y coincidió con la referencia previa del mismo teléfono en modo de
desarrollo (cinco fotografías) o con la ruta reproducida en computadora (`IMG_20260912_071121`, diferencia relativa de
peso 3.8·10⁻⁸ y de confianza 3·10⁻⁶). Los tres rechazos se conservan como `sin_vaca`. Los kilogramos son salida del
paquete de peso vigente el 19 de septiembre de 2026 (el del piloto), no pesos medidos: esta medición es de rendimiento
y paridad, no de exactitud.

## Lectura

RNF-02 (≤ 3 s por fotografía) no se cumple con originales de 12 MP: 25.5–29.1 s por fotografía aceptada. El modelo no es
el cuello de botella (2 % del tiempo); lo son dos bucles en JavaScript, la decodificación JPEG y la detección del
marcador a resolución completa. El banco de agosto (`benchmark_a25_20260826_fullres.json`, fotografías de 1280×960, ≈ 2.0 s
por fotografía) no representa esta latencia. Vías de optimización identificadas y no aplicadas: submuestrear la imagen
antes de detectar el marcador y sacar la decodificación JPEG de JavaScript.
