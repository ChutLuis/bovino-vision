# IoU contra el conjunto de validación manual — 2026-09-09

Referencia: `/home/luisc/Documents/bovino-vision/pipeline/data/val_clean` (40 imágenes, 24 animales, GT = png, objetivo = inst0). conf 0.45, imgsz 640, selección = mayor área.

Modelos:

- `preentrenado`: `/home/luisc/Documents/bovino-vision/pipeline/models/yolo26n-seg.pt` (clase 19, sha256 361fbfabab285c32…)
- `afinado_jun10`: `/home/luisc/Documents/bovino-vision/pipeline/models/yolo26n-seg-finetuned.pt` (clase 0, sha256 d6c65749431c100b…)

## total

| modelo | n | eligió objetivo % | sin detección | IoU objetivo | % IoU>0.5 | err área medio % | |err área| % | IoU emparejado | recall inst | FP |
|---|---|---|---|---|---|---|---|---|---|---|
| preentrenado | 40 | 92.5 | 1 | 0.851 | 92.5 | 4.1 | 9.1 | 0.759 | 0.846 | 16 |
| afinado_jun10 | 40 | 82.5 | 6 | 0.725 | 82.5 | -13.2 | 21.1 | 0.5 | 0.569 | 1 |

## facil

| modelo | n | eligió objetivo % | sin detección | IoU objetivo | % IoU>0.5 | err área medio % | |err área| % | IoU emparejado | recall inst | FP |
|---|---|---|---|---|---|---|---|---|---|---|
| preentrenado | 15 | 100.0 | 0 | 0.929 | 100.0 | 4.2 | 4.2 | 0.929 | 1.0 | 5 |
| afinado_jun10 | 15 | 93.3 | 1 | 0.83 | 93.3 | -8.4 | 8.9 | 0.83 | 0.933 | 1 |

## media

| modelo | n | eligió objetivo % | sin detección | IoU objetivo | % IoU>0.5 | err área medio % | |err área| % | IoU emparejado | recall inst | FP |
|---|---|---|---|---|---|---|---|---|---|---|
| preentrenado | 15 | 86.7 | 0 | 0.78 | 86.7 | 10.7 | 10.7 | 0.579 | 0.691 | 9 |
| afinado_jun10 | 15 | 86.7 | 1 | 0.756 | 86.7 | 3.0 | 17.5 | 0.275 | 0.316 | 0 |

## dificil

| modelo | n | eligió objetivo % | sin detección | IoU objetivo | % IoU>0.5 | err área medio % | |err área| % | IoU emparejado | recall inst | FP |
|---|---|---|---|---|---|---|---|---|---|---|
| preentrenado | 10 | 90.0 | 1 | 0.841 | 90.0 | -5.9 | 14.1 | 0.774 | 0.85 | 2 |
| afinado_jun10 | 10 | 60.0 | 4 | 0.52 | 60.0 | -44.7 | 44.7 | 0.343 | 0.4 | 0 |

## Bootstrap por animal (5000 remuestreos, semilla 0), diferencia contra `preentrenado`

- `afinado_jun10` − `preentrenado` en IoU objetivo: media -0.1278, IC95 [-0.2331, -0.0313]; en error de área: media -0.1821, IC95 [-0.2909, -0.0952] (n=24 animales)
