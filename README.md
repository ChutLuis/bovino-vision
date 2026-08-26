# Bovino Vision — Estimación de peso bovino por visión por computadora

Sistema de bajo costo para estimar el peso vivo de ganado Jersey a partir de una
fotografía lateral con un marcador ArUco de escala. Trabajo de graduación,
Universidad Rafael Landívar (Luis Felipe Chutá Ortiz).

**Pipeline:** foto lateral → segmentación (YOLO26n-seg) → escala métrica
(ArUco 15 cm, px→cm) → morfometría (área lateral) → modelo alométrico
W = a·A^b → peso vivo estimado.

## Estructura del repositorio

| Directorio | Contenido |
|---|---|
| `pipeline/` | Pipeline Python de investigación: captura, anotación, extracción morfométrica, ajuste del modelo de peso, evaluaciones y herramientas de paridad. Corre en PC — aquí ocurre TODO el entrenamiento/ajuste. |
| `app-benchmark/` | App Expo/React Native de benchmark: validó en un Galaxy A25 la inferencia LiteRT, el ArUco móvil y las paridades contra el pipeline (spike GO, ago 2026). Herramienta interna, no producto. |
| `app/` | APK de producto (React Native + Expo): foto → peso, 100% offline. |
| `docs/` | Requerimientos, protocolo de campo, arquitectura y decisiones, UI/UX. |
| `informes/` | Resultados crudos de benchmarks y golden tests. |
| `notebooks/` | Análisis estadístico reproducible. |
| `data/` | Muestras curadas (los datos crudos de campo viven fuera del repo con manifiesto SHA-1). |

## Documentos clave
- [Requerimientos y producto final](docs/01_requerimientos.md)
- [Protocolo de campo](docs/02_protocolo_campo.md)
- [Arquitectura del APK y decisiones (con evolución documentada)](docs/03_arquitectura_apk.md)
- [UI/UX y contrato de artefactos](docs/04_ui_ux.md)

## Principios del proyecto
1. **El teléfono nunca aprende**: ejecuta artefactos congelados (modelo + coeficientes
   versionados) entrenados y validados en `pipeline/`.
2. **Toda decisión tiene evidencia**: benchmarks para rendimiento, paridades para
   fidelidad de instrumento, golden tests para correctitud de implementación.
3. **Transparencia**: los fallos y cambios de decisión se documentan, no se borran
   (ver evolución D1/D3 en la arquitectura).
