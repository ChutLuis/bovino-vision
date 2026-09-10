# IoU contra el conjunto de validación manual — 2026-09-09

Referencia: `/home/luisc/Documents/bovino-vision/pipeline/data/val_clean` (40 imágenes, 24 animales, GT = png, objetivo = inst0). conf 0.5, imgsz 640, selección = mayor área.

Modelos:

- `pt`: `/home/luisc/Documents/bovino-vision/pipeline/models/yolo26n-seg.pt` (clase 19, sha256 361fbfabab285c32…)
- `apk`: `/home/luisc/Documents/bovino-vision/pipeline/../app/assets/model_bundle/yolo26n-seg.tflite` (clase 19, sha256 14b35a7ba712f8b0…)

## total

| modelo | n | eligió objetivo % | sin detección | IoU objetivo | % IoU>0.5 | err área medio % | |err área| % | IoU emparejado | recall inst | FP |
|---|---|---|---|---|---|---|---|---|---|---|
| pt | 40 | 90.0 | 2 | 0.828 | 90.0 | 1.5 | 11.5 | 0.715 | 0.796 | 11 |
| apk | 40 | 95.0 | 0 | 0.868 | 95.0 | 7.2 | 7.2 | 0.766 | 0.859 | 13 |

## facil

| modelo | n | eligió objetivo % | sin detección | IoU objetivo | % IoU>0.5 | err área medio % | |err área| % | IoU emparejado | recall inst | FP |
|---|---|---|---|---|---|---|---|---|---|---|
| pt | 15 | 100.0 | 0 | 0.929 | 100.0 | 4.2 | 4.2 | 0.929 | 1.0 | 4 |
| apk | 15 | 100.0 | 0 | 0.924 | 100.0 | 3.8 | 3.8 | 0.924 | 1.0 | 5 |

## media

| modelo | n | eligió objetivo % | sin detección | IoU objetivo | % IoU>0.5 | err área medio % | |err área| % | IoU emparejado | recall inst | FP |
|---|---|---|---|---|---|---|---|---|---|---|
| pt | 15 | 86.7 | 0 | 0.78 | 86.7 | 10.7 | 10.7 | 0.549 | 0.657 | 6 |
| apk | 15 | 86.7 | 0 | 0.77 | 86.7 | 12.3 | 12.3 | 0.567 | 0.691 | 6 |

## dificil

| modelo | n | eligió objetivo % | sin detección | IoU objetivo | % IoU>0.5 | err área medio % | |err área| % | IoU emparejado | recall inst | FP |
|---|---|---|---|---|---|---|---|---|---|---|
| pt | 10 | 80.0 | 2 | 0.748 | 80.0 | -16.3 | 23.7 | 0.646 | 0.7 | 1 |
| apk | 10 | 100.0 | 0 | 0.932 | 100.0 | 4.9 | 4.9 | 0.826 | 0.9 | 2 |

## Bootstrap por animal (5000 remuestreos, semilla 0), diferencia contra `pt`

- `apk` − `pt` en IoU objetivo: media 0.0239, IC95 [-0.0061, 0.0723]; en error de área: media 0.0359, IC95 [-0.0004, 0.0882] (n=24 animales)
