# Requerimientos del Proyecto — Sistema de Estimación de Peso Bovino

## 1. Definición del producto final

**Producto:** Aplicación móvil Android (APK) que estima el peso vivo de ganado bovino
Jersey adulto a partir de una fotografía lateral tomada con el teléfono, operando
completamente sin conexión a internet (inferencia on-device).

**Usuario objetivo:** pequeño y mediano productor ganadero guatemalteco
(hatos de 5–50 animales, ingreso sectorial promedio Q1,750/mes — MAGA 2023).

**Propuesta de valor (una oración):** pesar el ganado con una foto del teléfono —
sin báscula, sin internet y sin confinar al animal — con un error menor al 10%
(7.71% medido en el piloto de campo), por menos del costo de una sola sesión de
pesaje rentado (≈ Q2,000).

## 2. Requerimientos funcionales

| ID | Requerimiento | Prioridad |
|---|---|---|
| RF-01 | Capturar o seleccionar una fotografía lateral del animal desde la app | Alta |
| RF-02 | Detectar y segmentar la silueta del bovino (YOLO26-seg on-device) | Alta |
| RF-03 | Detectar y decodificar el marcador ArUco de escala (15 cm, DICT_6X6_250) y convertir píxeles a centímetros | Alta |
| RF-04 | Calcular características morfométricas (área lateral, longitud, altura) | Alta |
| RF-05 | Estimar el peso vivo con el modelo alométrico W = a·A^b e informar intervalo de predicción (± kg, 95%) | Alta |
| RF-06 | Mostrar la silueta segmentada superpuesta sobre la foto (feedback visual) | Alta |
| RF-07 | Rechazar con mensaje claro las capturas inválidas (sin animal, sin marcador, marcador ilegible) | Alta |
| RF-08 | Guardar cada estimación en base de datos local (SQLite): foto, peso, fecha, ID de animal | Media |
| RF-09 | Registrar/seleccionar animales por identificador (número de arete, manual) | Media |
| RF-10 | Mostrar historial de pesos por animal (tabla y gráfica de tendencia) | Media |
| RF-11 | Exportar el historial a CSV para compartir | Baja |

## 3. Requerimientos no funcionales

| ID | Requerimiento | Métrica verificable |
|---|---|---|
| RNF-01 | Operación 100% offline | Ninguna llamada de red en el flujo de estimación |
| RNF-02 | Tiempo de inferencia aceptable en gama media | ≤ 3 s por foto — **medido en Galaxy A25: ~2.0 s** (segmentación 0.45 s + ArUco full-res 1.4 s + postproceso 0.15 s); cold start 3.97 s mitigado con precarga al abrir la app |
| RNF-03 | Precisión heredada del modelo validado | MAPE < 10 % en condiciones del protocolo de captura (umbral H1a). Campaña de calibración: 7.72 %, IC95 [5.98, 9.57], 40 animales con referencia (cinta bovinométrica del 20 de septiembre de 2026, una lectura), una fotografía por animal, LOO por animal, bundle `campana-994d9c2cd1a6` (`informes/campana_20260912/peso/`). Piloto: 7.71 %, IC95 [6.2, 9.2], n = 34. La ruta del APK reproduce las áreas del pipeline con diferencia ≤ 1 % (`informes/paridad_segmentador_20260909/`) |
| RNF-04 | Tamaño de la app razonable para descarga rural | APK ≤ 80 MB (modelo YOLO26n-seg LiteRT FP32: 12 MB medidos) |
| RNF-05 | Compatibilidad | Android 7.0+ (API 24), sin requerir GPU dedicada |
| RNF-06 | Privacidad de datos | Todos los datos permanecen en el dispositivo del productor |
| RNF-07 | Usabilidad rural | Flujo foto→peso en ≤ 3 toques; textos en español; iconografía clara |

## 4. Restricciones y supuestos

- El modelo de peso es válido para vacas Jersey adultas (293–449 kg del hato piloto);
  la ampliación de rango depende de la campaña de campo de septiembre 2026.
- Requiere el marcador ArUco de 15 cm visible en la escena, en el plano del costado
  del animal (limitación de escala documentada en §5.2 de la tesis).
- Fotografía lateral, animal de pie, luz diurna (variables de control de la tesis).
- El Jetson Orin Nano queda documentado como plataforma de validación del prototipo
  y como línea futura de "estación de corral" para monitoreo continuo (Cap. 7).

## 5. Fuera de alcance (esta versión)

- Identificación automática del animal (RFID / OCR de arete) — trabajo futuro declarado.
- Integración con SINAT-GT.
- Estimación en video continuo o en pastoreo abierto.
- Versión iOS.
