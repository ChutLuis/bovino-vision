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
| `notebooks/` | `modelo_peso.ipynb`, ejecutado: datos de la sesión de campo del 12 de septiembre de 2026 (40 animales, una fotografía por animal), ajuste W = a·A^b con leave-one-out por animal, coeficientes e intervalo del paquete, repetibilidad entre fotografías, predictor alternativo explorado, fotografías con el marcador, IoU del segmentador, paridad PC↔A25, tiempos (1280×960 y originales de 12 MP), golden, y el modelo del piloto con su transferencia a la sesión de campo del 12 de septiembre de 2026. |

Los datos crudos de campo viven fuera del repositorio (`Thesis_final_raw/`, con `MANIFEST.sha1`); el repositorio lleva
las fotos curadas, los pesos y el conjunto de validación anotado en `pipeline/data/`.

## Documentos clave
- [Requerimientos y producto final](docs/01_requerimientos.md)
- [Protocolo de campo](docs/02_protocolo_campo.md)
- [Arquitectura de la aplicación: componentes, secuencia, flujos de datos y almacenamiento](docs/03_arquitectura_apk.md)
- [Interfaz de la aplicación](docs/04_ui_ux.md)

## Licencia

Copyright (C) 2026 Luis Felipe Chutá Ortiz.

- **Código** (`pipeline/`, `app/`, `app-benchmark/`, `notebooks/`): [GNU Affero General Public License v3.0 o
  posterior](LICENSE). `pipeline/` importa el paquete `ultralytics` y la aplicación empaqueta un modelo derivado de sus
  pesos, ambos bajo AGPL-3.0; la misma licencia para el código propio evita incompatibilidades y obliga a publicar el
  código fuente de cualquier versión modificada que se distribuya o se ofrezca como servicio. Un producto comercial de
  código cerrado exigiría la licencia empresarial de Ultralytics o un segmentador alternativo, además de un acuerdo
  con el autor sobre su propio código.
- **Datos, informes y documentación** (`pipeline/data/`, `informes/`, `docs/`):
  [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/deed.es).
- **Componentes de terceros** conservan sus licencias: Ultralytics YOLO26n-seg (AGPL-3.0); React Native, Expo y
  react-native-fast-tflite (MIT); jpeg-js (BSD-3-Clause); js-aruco2 (MIT, con avisos de ArUco, OpenCV y AForge.NET en
  su `LICENSE.txt`, que se conservan); OpenCV y LiteRT (Apache 2.0).

## Principios del proyecto
1. **El teléfono nunca aprende**: ejecuta artefactos congelados (modelo + coeficientes
   versionados) entrenados y validados en `pipeline/`.
2. **Toda decisión tiene evidencia**: benchmarks para rendimiento, paridades para
   fidelidad de instrumento, golden tests para correctitud de implementación.
3. **Trazabilidad**: cada estimación guarda la versión del modelo de peso y el hash del
   segmentador que la produjeron.
