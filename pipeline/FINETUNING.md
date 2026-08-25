# Fine-tuning de YOLO26-seg (pipeline listo)

Objetivo: especializar el segmentador en las vacas Jersey de la finca usando **tus 790 máscaras**,
con data augmentation real. Independiente del modelo de peso (NO lo cambia).

## Pasos
```bash
cd prototype

# 1) Generar dataset YOLO-seg (split POR ANIMAL, sin fuga). Ya verificado: 790 imgs, 28 animales.
python3 src/build_yolo_seg_dataset.py
#   -> data/field/seg_dataset/{images,labels}/{train,val} + data.yaml
#   -> train 614 / val 176 ; val held-out: AMBAR, ESTRELLITA, KARINA, NAHOMI, ODRA, TATY

# 2) Entrenar (augmentation activado). Mac: --device mps ; Jetson: --device cuda:0 ; sin GPU: --device cpu
python3 src/finetune_segmenter.py --device mps --epochs 80
#   -> runs/seg_finetune/jersey/weights/best.pt

# 3) Evaluar held-out: fine-tuned vs preentrenado (misma referencia)
python3 src/eval_finetuned_iou.py --finetuned runs/seg_finetune/jersey/weights/best.pt --device mps
```

## Qué APORTA (honesto)
- Usa **todas las 790 máscaras** como datos de entrenamiento (no solo 40 de referencia).
- **Vuelve real el data augmentation** del Cap 3 (lo aplica Ultralytics).
- Reduce la brecha diseño↔ejecutado (Cap 3 prometía transfer learning + split por animal).
- Suma sustancia de ingeniería ("modelo entrenado propio").

## Qué NO cambia
- **El resultado de peso (MAPE/H1a) NO cambia** — depende de la escala (marcador), no de la máscara.
- La mejora de IoU es **incierta**: el preentrenado ya es muy bueno.

## ⚠️ CAVEAT CRÍTICO DE EVALUACIÓN (leer antes de reportar nada)
Muchas máscaras en `mascaras/` fueron **auto-generadas por YOLO** (las "listas" del `auto_mask.py`),
no dibujadas a mano. Eso **rompe la evaluación de IoU**:
- Si el ground-truth de val es una máscara que YOLO mismo generó, el preentrenado obtiene IoU ≈ 0.98
  (se compara contra su propia salida), y el fine-tuned podría salir **artificialmente más bajo** solo
  por haberse desviado de esa salida. Es decir, **el test penalizaría injustamente al fine-tuning.**
- Verificado: IoU preentrenado en val ≈ 0.98 → señal de que el GT de val es mayormente auto.

**Para una comparación honesta y publicable**, el conjunto de evaluación debe usar **máscaras
dibujadas a mano** (referencia independiente del modelo). Opciones:
1. Dibujar a mano ~20–30 máscaras de referencia sobre los animales de val (held-out) y evaluar contra esas.
2. Identificar cuáles de tus máscaras fueron hechas a mano (revisar/draw_mask) y restringir val a esas.

Sin eso, **entrena y usa el modelo, pero NO afirmes una mejora de IoU** — el número no sería confiable.
La evaluación `eval_finetuned_iou.py` es una **comparación relativa**; interprétala solo si el GT de
val es de máscaras a mano.

## Recomendación
- Para "usar todos los datos + augmentation real + cerrar la brecha del Cap 3": **vale**, corre 1) y 2).
- Para **reportar un IoU mejorado en la tesis**: requiere el conjunto de evaluación a mano (paso del caveat).
  Sin eso, repórtalo solo como "modelo afinado disponible (trabajo futuro: evaluación con anotación independiente)".
