# Paridad del segmentador — 2026-09-09

.pt `yolo26n-seg.pt` (sha256 361fbfabab285c32…) vs LiteRT `yolo26n-seg.tflite` (sha256 14b35a7ba712f8b0…), conf 0.5, clase 19, selección = mayor área.

## A. Emulación LiteRT en PC vs Galaxy A25 (10 fotos del benchmark, 26 ago 2026)

- Mismo número de detecciones en 10 de 10 fotos.
- Área PC-LiteRT vs A25: media -0.014 %, |máx| 0.205 %.
- Confianza: |dif| máx 0.0057. Caja: |dif| máx 1.17 px.

## A'. LiteRT vs .pt en las mismas 10 fotos

- Área: media -0.252 %, |media| 0.376 %, |máx| 0.619 %. Criterio ≤ 1 %: PASA.
- IoU entre máscaras: media 0.964, mín 0.956.

## B. .pt vs LiteRT en las 40 imágenes manuales

| estrato | n | mismas detecciones | IoU pt↔LiteRT (media / mín) | dif. área % (media / \|máx\|) | misma decisión objetivo | eligió objetivo pt / LiteRT | IoU objetivo pt / LiteRT |
|---|---|---|---|---|---|---|---|
| facil | 15 | 14 | 0.962 / 0.9553 | -0.41 / 1.47 | 15 | 15 / 15 | 0.929 / 0.924 |
| media | 15 | 14 | 0.945 / 0.8533 | 1.217 / 14.2 | 15 | 13 / 13 | 0.78 / 0.77 |
| dificil | 10 | 7 | 0.966 / 0.9582 | 0.419 / 2.0 | 8 | 8 / 10 | 0.748 / 0.932 |
| total | 40 | 35 | 0.956 / 0.8533 | 0.407 / 14.2 | 38 | 36 / 38 | 0.828 / 0.868 |
