# Interfaz de la aplicación

Wakx ("vaca" en kaqchikel), subtítulo "Estimación de peso bovino". Usuario: pequeño productor rural que usa la app al
aire libre, bajo sol directo, con una mano y sin vocabulario técnico.

## Restricciones de diseño

1. Sol directo: contraste alto, texto grande, nada de grises sutiles.
2. Una mano: acciones principales al alcance del pulgar, botones de al menos 56 px.
3. Sin jerga: el ganadero "pesa"; nunca "segmentación", "confianza" ni "inferencia". El marcador ArUco se llama "cuadro".
4. Sin red: ningún estado de la interfaz depende de conectividad.
5. Foto → peso en pocos toques (RNF-07).

## Pantallas

| Pantalla | Qué hace |
|---|---|
| Arranque (`SplashScreen`) | Carga el modelo una sola vez (3.97 s en frío en el A25) antes de habilitar la captura. La primera vez muestra `OnboardingScreen`: cuatro tarjetas ("Pese con una foto.", "El cuadro es la regla.", "De lado y entera.", "Listo para pesar.") y la lista de requisitos de la foto; la guía se puede reabrir desde la captura. |
| Captura (`CapturaScreen`) | Tomar la foto o elegirla de la galería; foto de ejemplo del encuadre; acceso al historial. |
| Procesando (`ProcesandoScreen`) | Etapas sobre la foto ("Animal encontrado", "Leyendo el cuadro…", "Calculando el peso") legibles al sol, con cancelación explícita. |
| Resultado (`ResultadoScreen`) | Peso en grande en kilogramos, debajo en libras y el margen ± de la estimación, silueta pintada sobre la foto y recuadro del cuadro; campo de arete de seis dígitos con aviso si el animal ya está en el historial; guardar o repetir la foto. Si la foto no sirve: la causa en lenguaje de corral ("No se ve la vaca completa", "No se ve el cuadro", "El cuadro no se puede leer"), qué hacer, y un solo botón para volver a tomar. |
| Historial (`HistorialScreen`) | Animales por arete con búsqueda; detalle con las pesadas, la diferencia contra la anterior y la tendencia; borrado por deslizamiento; compartir el historial en CSV. |

## Contrato con el pipeline

La app consume `app/assets/model_bundle/`: `yolo26n-seg.tflite`, `model_manifest.json`, `weight_model.json`
(`a`, `b`, `interval`, `version`, `fuente`, `calibration`) y `golden_cases.json`. El intervalo de predicción al 95 % se calcula
en la app a partir de `interval`; la pantalla lo muestra como «Margen ± N kg», con N la mitad de la anchura del intervalo
redondeada a kilos enteros (el intervalo exacto es asimétrico porque se construye en escala logarítmica), y añade
«foto fuera del rango calibrado, el margen puede ser mayor» cuando el área queda fuera de `area_min`–`area_max`; si el
bundle trae `interval = null`, la pantalla dice «Margen no disponible» en lugar de inventar uno. El peso se muestra en
kilogramos y, debajo, en libras (factor 0.45359237), que es la unidad de la hoja de pesaje de la finca.
Los coeficientes nunca se escriben en el código: al reajustar el modelo con la campaña de calibración cambia solo el
paquete y su versión, y cada estimación guarda con qué versión se calculó (`docs/03_arquitectura_apk.md`).
