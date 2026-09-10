# Regla de selección de la vaca objetivo — 2026-09-10

Modelo: `yolo26n-seg.tflite` (ruta del APK en PC, conf 0.5). Referencia: 40 imágenes manuales de `data/val_clean`, inst0 = vaca pesada.
Con marcador ArUco detectado: 39/40 (id 0: 39). Con más de una detección: 23/40. Sin detección: 0.
Oráculo (alguna detección con IoU ≥ 0.5 contra la vaca objetivo): 40/40; objetivo NO detectado en: ninguna.

| regla | eligió objetivo | IoU objetivo medio | cambia vs area | mejora | empeora |
|---|---|---|---|---|---|
| area | 38/40 | 0.8684 | 0 | 0 | 0 |
| marcador_dist | 28/40 | 0.6445 | 12 | 0 | 10 |
| centro_x | 26/40 | 0.5982 | 14 | 0 | 12 |
| franja_0 | 34/40 | 0.7823 | 6 | 0 | 4 |
| franja_1 | 29/40 | 0.6666 | 11 | 0 | 9 |
| franja_2 | 31/40 | 0.7138 | 9 | 0 | 7 |

## Fotos que cambian de decisión respecto a `area`

- **marcador_dist**: 5_06_odra, 5_06_karina, burst_ambar_01, burst_ambar_02, burst_ambar_03, burst_estrellita_01, burst_estrellita_02, burst_taty_02, burst_nahomi_01, burst_nahomi_02, 12_06_lubianca, 12_06_zafiro — empeora: 5_06_odra, 5_06_karina, burst_ambar_01, burst_ambar_02, burst_ambar_03, burst_estrellita_01, burst_estrellita_02, burst_taty_02, 12_06_lubianca, 12_06_zafiro
- **centro_x**: 5_06_odra, 5_06_cristy, 5_06_zafiro, 5_06_karina, burst_ambar_01, burst_ambar_02, burst_ambar_03, burst_estrellita_01, burst_estrellita_02, burst_taty_02, burst_nahomi_01, burst_nahomi_02, 12_06_lubianca, 12_06_zafiro — empeora: 5_06_odra, 5_06_cristy, 5_06_zafiro, 5_06_karina, burst_ambar_01, burst_ambar_02, burst_ambar_03, burst_estrellita_01, burst_estrellita_02, burst_taty_02, 12_06_lubianca, 12_06_zafiro
- **franja_0**: burst_ambar_01, burst_ambar_02, burst_ambar_03, burst_estrellita_01, burst_nahomi_01, burst_nahomi_02 — empeora: burst_ambar_01, burst_ambar_02, burst_ambar_03, burst_estrellita_01
- **franja_1**: 5_06_odra, 5_06_karina, burst_ambar_01, burst_ambar_02, burst_ambar_03, burst_estrellita_01, burst_estrellita_02, burst_nahomi_01, burst_nahomi_02, 12_06_lubianca, 12_06_zafiro — empeora: 5_06_odra, 5_06_karina, burst_ambar_01, burst_ambar_02, burst_ambar_03, burst_estrellita_01, burst_estrellita_02, 12_06_lubianca, 12_06_zafiro
- **franja_2**: 5_06_odra, 5_06_karina, burst_ambar_01, burst_ambar_02, burst_ambar_03, burst_estrellita_01, burst_estrellita_02, burst_nahomi_01, burst_nahomi_02 — empeora: 5_06_odra, 5_06_karina, burst_ambar_01, burst_ambar_02, burst_ambar_03, burst_estrellita_01, burst_estrellita_02

## Fotos con más de una detección

| qid | estrato | dets | marcador | marcador dentro de la caja de inst0 | oráculo | area | marcador_dist | centro_x | franja_0 | franja_1 | franja_2 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 5_06_perla | facil | 2 | no |  | ok (#0, IoU 0.9355) | ok (#0) | ok (#0) | ok (#0) | ok (#0) | ok (#0) | ok (#0) |
| 5_06_odra | facil | 2 | id 0 | 0 | ok (#0, IoU 0.9301) | ok (#0) | X (#1) | X (#1) | ok (#0) | X (#1) | X (#1) |
| 5_06_cristy | facil | 2 | id 0 | 0 | ok (#0, IoU 0.9239) | ok (#0) | ok (#0) | X (#1) | ok (#0) | ok (#0) | ok (#0) |
| 5_06_zafiro | facil | 2 | id 0 | 0 | ok (#0, IoU 0.9212) | ok (#0) | ok (#0) | X (#1) | ok (#0) | ok (#0) | ok (#0) |
| 5_06_karina | facil | 2 | id 0 | 0 | ok (#0, IoU 0.9356) | ok (#0) | X (#1) | X (#1) | ok (#0) | X (#1) | X (#1) |
| burst_ambar_01 | media | 6 | id 0 | 0 | ok (#0, IoU 0.916) | ok (#0) | X (#2) | X (#3) | X (#3) | X (#3) | X (#3) |
| burst_ambar_02 | media | 4 | id 0 | 0 | ok (#0, IoU 0.8386) | ok (#0) | X (#3) | X (#3) | X (#3) | X (#3) | X (#3) |
| burst_ambar_03 | media | 5 | id 0 | 0 | ok (#0, IoU 0.8832) | ok (#0) | X (#2) | X (#2) | X (#2) | X (#4) | X (#4) |
| burst_estrellita_01 | media | 5 | id 0 | 0 | ok (#0, IoU 0.813) | ok (#0) | X (#4) | X (#4) | X (#4) | X (#4) | X (#4) |
| burst_estrellita_02 | media | 3 | id 0 | 0 | ok (#0, IoU 0.8778) | ok (#0) | X (#1) | X (#1) | ok (#0) | X (#1) | X (#1) |
| burst_estrellita_03 | media | 2 | id 0 | 0 | ok (#0, IoU 0.8398) | ok (#0) | ok (#0) | ok (#0) | ok (#0) | ok (#0) | ok (#0) |
| burst_taty_01 | media | 4 | id 0 | 0 | ok (#0, IoU 0.8725) | ok (#0) | ok (#0) | ok (#0) | ok (#0) | ok (#0) | ok (#0) |
| burst_taty_02 | media | 4 | id 0 | 0 | ok (#0, IoU 0.8886) | ok (#0) | X (#2) | X (#2) | ok (#0) | ok (#0) | ok (#0) |
| burst_nahomi_01 | media | 3 | id 0 | 0 | ok (#0, IoU 0.8551) | X (#2) | X (#1) | X (#1) | X (#1) | X (#1) | X (#1) |
| burst_nahomi_02 | media | 5 | id 0 | 0 | ok (#0, IoU 0.8509) | X (#2) | X (#4) | X (#4) | X (#4) | X (#4) | X (#4) |
| burst_karina_01 | media | 2 | id 0 | 0 | ok (#0, IoU 0.9124) | ok (#0) | ok (#0) | ok (#0) | ok (#0) | ok (#0) | ok (#0) |
| burst_karina_02 | media | 2 | id 0 | 0 | ok (#0, IoU 0.9249) | ok (#0) | ok (#0) | ok (#0) | ok (#0) | ok (#0) | ok (#0) |
| burst_odra_01 | media | 2 | id 0 | 0 | ok (#0, IoU 0.9111) | ok (#0) | ok (#0) | ok (#0) | ok (#0) | ok (#0) | ok (#0) |
| 12_06_diagira | dificil | 2 | id 0 | 1 | ok (#0, IoU 0.9287) | ok (#0) | ok (#0) | ok (#0) | ok (#0) | ok (#0) | ok (#0) |
| 12_06_lubianca | dificil | 2 | id 0 | 0 | ok (#0, IoU 0.9423) | ok (#0) | X (#1) | X (#1) | ok (#0) | X (#1) | ok (#0) |
| 12_06_mafer | dificil | 2 | id 0 | 0 | ok (#0, IoU 0.9147) | ok (#0) | ok (#0) | ok (#0) | ok (#0) | ok (#0) | ok (#0) |
| 12_06_zafiro | dificil | 2 | id 0 | 0 | ok (#0, IoU 0.9451) | ok (#0) | X (#1) | X (#1) | ok (#0) | X (#1) | ok (#0) |
| 12_06_selena | dificil | 2 | id 0 | 1 | ok (#0, IoU 0.9472) | ok (#0) | ok (#0) | ok (#0) | ok (#0) | ok (#0) | ok (#0) |

## Lectura

1. **El fallo de Nahomi no es de detección sino de selección**: la vaca pesada se recupera en ambas fotos
   (oráculo IoU 0.8551 y 0.8509), pero es la detección #0,
   no la de mayor área (#2, la vaca de frente en primer plano).
2. **Ninguna regla basada en el marcador la rescata.** En `img/burst_nahomi_01.jpg` el marcador lo sostiene una
   persona a la izquierda de la cabeza de la vaca objetivo, delante de las vacas del fondo; el segmentador
   devuelve una detección fusionada de esas vacas (#1, conf 0.81) cuya caja contiene al marcador, así que
   "más cercana al marcador", "centro_x" y "franja_k" la eligen a ella. La vaca objetivo no toca la columna del marcador.
3. **Las reglas por marcador empeoran el resto.** En `fotos_hoy` el marcador está en un poste a un costado
   (`5_06_odra`, `5_06_karina`: la vaca del fondo queda bajo el poste) y en las ráfagas con 4-6 animales
   (`burst_ambar_*`, `burst_estrellita_*`) el marcador rara vez cae sobre la vaca pesada. Resultado: 0 mejoras y
   entre 4 y 12 empeoramientos según la regla.
4. **"Mayor área" sigue siendo la mejor regla única** (38/40, IoU medio 0.8684) con el protocolo de captura
   de junio. No hay evidencia para cambiarla en el APK ni en RF-07.

## Propuesta (sin desplegar): guardia, no regla nueva

Mantener "mayor área" y añadir una **verificación de plausibilidad**: si la caja de la vaca elegida no solapa la
columna vertical del marcador (franja k = 0), la aplicación avisa "hay varias vacas; confirme que la resaltada es
la del arete" en vez de cambiar la elección en silencio. Sobre las 40 manuales la guardia se dispararía en
6 fotos: 2 verdaderas (burst_nahomi_01, burst_nahomi_02) y 4 falsas alarmas (burst_ambar_01, burst_ambar_02, burst_ambar_03, burst_estrellita_01), todas estas
con el marcador en un poste o lejos del costado. Con el protocolo de la campaña de calibración (marcador en
contacto con el costado del animal, Fase 6 de la tesis) la falsa alarma debería desaparecer y la guardia se
vuelve exacta; conviene medirlo sobre las fotos de septiembre antes de tocar `segment.ts`.

Coste en la app: un solape de cajas por foto (ya se tienen la caja de la vaca y las esquinas del marcador en
`estimarPeso.ts`); no cambia el modelo ni el postproceso.

## Reproducir

```
cd pipeline && .venv/bin/python src/eval_cow_selection.py --visual   # ~1 min en CPU, escribe informes/seleccion_vaca_<fecha>/
```
