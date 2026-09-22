# Paridad en el dispositivo del predictor de profundidad

Comparación, fotografía por fotografía, entre la computadora y el teléfono de referencia de las magnitudes
que produce la cadena de visión de la aplicación y el predictor de profundidad corporal proyectada
(`D_media`), sobre las 40 fotografías primarias de la sesión de campo del 12 de septiembre de 2026.

## Condiciones

| Campo | Valor |
|---|---|
| Fecha de la medición | 21 de septiembre de 2026 |
| Dispositivo | Samsung Galaxy A25 (SM-A256E), Android 16 |
| Compilación | Aislada, `applicationId` `com.luisc.wakx.depth`, con el mismo código de visión que la aplicación (decodificación con jpeg-js, lienzo de 640 px, segmentador LiteRT FP32, lectura del marcador con js-aruco2) más el cálculo de `D_media`. No es el paquete de instalación entregado |
| Fotografías | Las 40 primarias, una por animal, las mismas del ajuste del modelo de peso |
| Referencia | La misma cadena ejecutada en computadora |
| Predictor | `W = a · D_media`, paquete `campana-depth-994d9c2cd1a6` |

## Resultado

| Magnitud comparada | Diferencia máxima entre teléfono y computadora |
|---|---|
| Área de la máscara, en píxeles | 0 |
| Escala, en cm/px | 0.0 |
| `D_media`, en cm | 0.0 |
| Peso del predictor de profundidad, en kg | 0.0 |
| Límites del intervalo de predicción al 95 %, en kg | 5.7 × 10⁻¹⁴ |
| sha256 de la máscara | Igual en 40 de 40 |
| Fotografías comparadas | 40 de 40, todas con estado `ok` en ambos lados |

Costo adicional del cálculo de `D_media` en el teléfono, por fotografía: mediana 414.5 ms, media 416.2 ms,
mínimo 358.7 ms, máximo 499.7 ms.

## Alcance

La compilación aislada no es la aplicación entregada, que estima con el área lateral y no calcula `D_media`.
Lo que esta medición sí cubre para la aplicación entregada son las magnitudes compartidas: la máscara, su
área en píxeles y la escala del marcador, idénticas en las 40 fotografías. El peso del modelo de área no se
calculó en esta corrida. La verificación de la cadena completa fotografía → peso del paquete de instalación
entregado se hizo por separado sobre cinco fotografías.

## Archivos

- `paridad_a25.csv`: una fila por fotografía, con los valores de la computadora (`_pc`), los del teléfono
  (`_tel`) y su diferencia (`dif_`) para el área en píxeles, la escala, `D_media`, el peso y los límites del
  intervalo; `sha_igual` indica si el sha256 de la máscara coincide; `depth_ms` y `sobrecosto_ms` son los
  tiempos del cálculo de profundidad en el teléfono; las columnas `dominio_` describen el rango de
  calibración del paquete.
- `paridad_a25.json`: resumen de la comparación y métricas del predictor recalculadas con los valores de
  `D_media` medidos en el teléfono.

El programa que emparejó ambas salidas no forma parte del repositorio; los valores de los dos lados se
conservan en el CSV para su verificación.
