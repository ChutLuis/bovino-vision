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
| `pipeline/` | Código Python de investigación (PC): anotación, segmentación, morfometría, ajuste del modelo de peso, evaluaciones y exportación del modelo. Todo el entrenamiento y la validación ocurren aquí. |
| `app/` | Wakx, la aplicación Android de producto (React Native + Expo): foto → peso, sin conexión. |
| `app-benchmark/` | App con la que se midió en un Galaxy A25 la inferencia LiteRT, el ArUco móvil y la paridad con el pipeline (agosto de 2026). Herramienta interna. |
| `docs/` | Requerimientos, protocolo de campo, arquitectura y UI. |
| `informes/` | Benchmarks, paridades, evaluaciones del segmentador y pruebas en dispositivo, con sus datos (JSON, CSV, PNG, SQLite). |

Los datos crudos de campo viven fuera del repositorio (`Thesis_final_raw/`, con `MANIFEST.sha1`); el repositorio lleva
las fotos curadas, los pesos y el conjunto de validación anotado en `pipeline/data/`.

## Documentos clave
- [Requerimientos y producto final](docs/01_requerimientos.md)
- [Protocolo de campo](docs/02_protocolo_campo.md)
- [Arquitectura de la aplicación: componentes, secuencia, flujos de datos y almacenamiento](docs/03_arquitectura_apk.md)
- [Interfaz de la aplicación](docs/04_ui_ux.md)

## Principios del proyecto
1. **El teléfono nunca aprende**: ejecuta artefactos congelados (modelo + coeficientes
   versionados) entrenados y validados en `pipeline/`.
2. **Toda decisión tiene evidencia**: benchmarks para rendimiento, paridades para
   fidelidad de instrumento, golden tests para correctitud de implementación.
3. **Trazabilidad**: cada estimación guarda la versión del modelo de peso y el hash del
   segmentador que la produjeron.
