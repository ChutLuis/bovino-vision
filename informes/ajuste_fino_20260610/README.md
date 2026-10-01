# Corrida de ajuste fino del segmentador (10 de junio de 2026)

Archivos que escribió Ultralytics 8.4.53 al ajustar `yolo26n-seg.pt` sobre el dataset YOLO-seg de junio de 2026
(`pipeline/FINETUNING.md`). La corrida se conserva tal cual; no se repitió.

| Archivo | Contenido |
|---|---|
| `args.yaml` | Configuración completa: 80 épocas con paciencia 20, entrada de 640 px, lote 8, semilla 0, aumentos de entrenamiento (mosaico 1.0, volteo horizontal 0.5, rotación ±10°, escala 0.4, HSV). `save_dir` conserva la ruta del equipo en el que corrió. |
| `results.csv` | 33 épocas registradas: la parada temprana detuvo el entrenamiento veinte épocas después de la mejor, la 13. |
| `confusion_matrix.png`, `confusion_matrix_normalized.png` | Matriz de confusión de la validación automática: 165 vacas detectadas, 11 no recuperadas y 29 predicciones sin vaca de referencia; la normalización es por columna. |
| `results.png` | Curvas de pérdida y métricas por época, tal como las dibuja Ultralytics. |

Los pesos no se versionan (`pipeline/models/*.pt`). `weights/best.pt` tiene sha256 `d6c65749431c100b…`, el registrado
para `yolo26n-seg-finetuned.pt` en `pipeline/models/README.md`; sus métricas guardadas son las de la época 13 (mAP50 de
máscara 0.921, mAP50-95 0.771). Sobre las 40 máscaras anotadas a mano el modelo afinado obtuvo IoU 0.725 frente a 0.851
del preentrenado (`informes/iou_val_manual_20260909/`), por lo que no se desplegó.
