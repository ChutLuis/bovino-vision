# IoU contra el conjunto de validación manual — 2026-09-09

Referencia: `/home/luisc/Documents/bovino-vision/pipeline/data/val_clean` (40 imágenes, 24 animales, GT = png, objetivo = inst0). conf 0.45, imgsz 640, selección = mayor área.

Modelos:

- `preentrenado`: `/home/luisc/Documents/bovino-vision/pipeline/models/yolo26n-seg.pt` (clase 19, sha256 361fbfabab285c32…)
- `afinado_jun10`: `/home/luisc/Documents/bovino-vision/pipeline/models/yolo26n-seg-finetuned.pt` (clase 0, sha256 d6c65749431c100b…)

## total

| modelo | n | eligió objetivo % | sin detección | IoU objetivo | % IoU>0.5 | err área medio % | |err área| % | IoU emparejado | recall inst | FP |
|---|---|---|---|---|---|---|---|---|---|---|
| preentrenado | 40 | 92.5 | 1 | 0.847 | 92.5 | 1.9 | 8.1 | 0.752 | 0.846 | 16 |
| afinado_jun10 | 40 | 82.5 | 6 | 0.718 | 82.5 | -15.3 | 19.9 | 0.498 | 0.569 | 1 |

## facil

| modelo | n | eligió objetivo % | sin detección | IoU objetivo | % IoU>0.5 | err área medio % | |err área| % | IoU emparejado | recall inst | FP |
|---|---|---|---|---|---|---|---|---|---|---|
| preentrenado | 15 | 100.0 | 0 | 0.929 | 100.0 | 4.2 | 4.2 | 0.929 | 1.0 | 5 |
| afinado_jun10 | 15 | 93.3 | 1 | 0.83 | 93.3 | -8.4 | 8.9 | 0.83 | 0.933 | 1 |

## media

| modelo | n | eligió objetivo % | sin detección | IoU objetivo | % IoU>0.5 | err área medio % | |err área| % | IoU emparejado | recall inst | FP |
|---|---|---|---|---|---|---|---|---|---|---|
| preentrenado | 15 | 86.7 | 0 | 0.769 | 86.7 | 4.7 | 7.8 | 0.56 | 0.691 | 9 |
| afinado_jun10 | 15 | 86.7 | 1 | 0.738 | 86.7 | -2.6 | 14.5 | 0.269 | 0.316 | 0 |

## dificil

| modelo | n | eligió objetivo % | sin detección | IoU objetivo | % IoU>0.5 | err área medio % | |err área| % | IoU emparejado | recall inst | FP |
|---|---|---|---|---|---|---|---|---|---|---|
| preentrenado | 10 | 90.0 | 1 | 0.841 | 90.0 | -5.8 | 14.2 | 0.774 | 0.85 | 2 |
| afinado_jun10 | 10 | 60.0 | 4 | 0.52 | 60.0 | -44.6 | 44.6 | 0.343 | 0.4 | 0 |

## Bootstrap por animal (5000 remuestreos, semilla 0), diferencia contra `preentrenado`

- `afinado_jun10` − `preentrenado` en IoU objetivo: media -0.1294, IC95 [-0.2345, -0.0336]; en error de área: media -0.1812, IC95 [-0.2891, -0.0946] (n=24 animales)
