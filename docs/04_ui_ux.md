# UI/UX del APK — Definición v1 y brief de diseño
**Correcciones atendidas: #2 (producto final), #6 (producto funcional)**
Estado: v0.1 — alcance mínimo acordado; nombre de la app pendiente de decisión
(candidatos: Wakx / Wakxalal (verificar con hablante kaqchikel) / EstiVac / BoviMetro)

## Alcance v1 (decidido 26 ago 2026)
- SIN feedback en vivo durante la cámara (frame processors quedan para v1.1).
- Flujo: captura → procesando (~2 s) → resultado con overlay → guardar.
- Historial mínimo: lista de estimaciones por animal. Gráfica de tendencia: v1.1.

## Contexto de uso (restricciones de diseño NO negociables)
1. **Sol directo de campo**: contraste alto, texto grande, nada de grises sutiles.
2. **Una sola mano**: acciones principales alcanzables con el pulgar, botones ≥ 56 px.
3. **Usuario no técnico**: el ganadero "pesa", no "infiere". Cero jerga
   (nunca "segmentación", "confianza del modelo", "inferencia").
4. **Offline siempre**: ningún estado de UI puede depender de red; no mostrar
   spinners de "conectando".
5. **Manos ocupadas/sucias**: flujo completo foto→peso en ≤ 3 toques (RNF-07).

## Pantallas y estados

### P1 — Captura
- Cámara a pantalla completa, lente principal 1x fijo.
- Guía visual estática (silueta punteada de vaca lateral + esquina donde suele
  quedar el marcador) — ayuda de encuadre, no detección en vivo.
- Botón único grande: disparador.

### P2 — Procesando (~2 s)
- La foto tomada de fondo + indicador de progreso con mensajes por etapa
  ("Buscando al animal…", "Leyendo el marcador…", "Calculando peso…").
- Corresponde al pipeline real: segmentación (0.45 s) → ArUco (1.4 s) → peso.

### P3a — Resultado (éxito) — LA pantalla de la demo
- Foto con **máscara de silueta superpuesta** (verde translúcido) y **marcador
  ArUco resaltado** (recuadro).
- Peso en tipografía gigante: **"375 kg"** + intervalo pequeño debajo ("± 24 kg").
- Acciones: [Guardar en historial] (elige/crea animal por arete) · [Repetir foto].

### P3b — Resultado (rechazo con causa, RF-07)
Mensajes en lenguaje de corral, cada uno con acción correctiva:
- Sin vaca detectada → "No se ve la vaca completa. Aléjese un poco y tome la
  foto de lado."
- Sin marcador → "No se ve el cuadro de referencia. Revise que esté visible y
  limpio."
- Marcador ilegible/inclinado → "El cuadro de referencia se ve borroso o de
  lado. Póngalo derecho, junto al costado de la vaca."
- Botón único: [Volver a tomar].

### P4 — Historial (v1 mínimo)
- Lista de animales (arete + nombre opcional); al tocar: estimaciones con fecha
  y peso. Botón exportar CSV (share intent).

### P0 — Arranque
- Splash con logo mientras se precarga el modelo (mitiga cold start 3.97 s).
- Regla: el modelo se carga UNA vez al abrir, nunca al tomar la foto.

## Brief para herramienta de diseño (copiar/pegar)

> Diseña una app Android para ganaderos guatemaltecos que estima el peso de una
> vaca a partir de una foto. Usuario: pequeño productor rural, poca familiaridad
> tecnológica, usa la app al aire libre bajo sol directo, con una sola mano.
> Estilo: cálido y confiable, no corporativo ni "startup"; alto contraste,
> tipografía grande, botones enormes; español sencillo de campo. 5 pantallas:
> (1) cámara con guía de encuadre punteada y un solo botón de disparo;
> (2) procesando con mensajes por etapa sobre la foto;
> (3) resultado: la foto con la silueta de la vaca pintada en verde translúcido,
> un recuadro sobre el marcador de referencia, y el peso enorme ("375 kg ± 24");
> botones Guardar y Repetir;
> (4) rechazo: mensaje claro de qué salió mal y cómo corregirlo, botón Volver a
> tomar; (5) historial: lista simple de animales y sus pesos con fechas.
> Paleta sugerida: verdes de campo + tierra, acentos de alta visibilidad.
> El nombre de la app es [NOMBRE] con subtítulo "Estimación de peso bovino".

## Contrato de artefactos congelados (pipeline → APK)
El APK consume un paquete versionado generado por `pipeline/`:
```
model_bundle/
├── yolo26n-seg.tflite     # LiteRT FP32 (12 MB), validado por paridad
├── weight_model.json      # { "a": 0.375, "b": 0.706, "interval": {...},
│                          #   "version": "2026-08-26", "fuente": "n=34 lateral" }
└── golden_cases.json      # casos foto→peso esperado (test de correctitud)
```
Regla: a y b NUNCA se escriben en el código de la app — siempre se leen del
bundle. Al re-ajustar con los datos de campo de sep 2026, solo cambia el bundle
y su versión (cada estimación guarda `versión_modelo` en SQLite).
