# Repetibilidad de los dos predictores entre fotografías del mismo animal

Fotografías preseleccionadas a 3 m aceptadas por la ruta de la aplicación y con profundidad medida; el peso de cada fotografía se predice con el ajuste completo de cada modelo. El ICC(1) del logaritmo del predictor es el del logaritmo del peso predicho. El coeficiente de variación y el rango del peso predicho por animal son la dispersión que ve el usuario al repetir la fotografía.

| Predictor | Fotografías | Animales | ICC(1) log | CV del peso: mediana | CV: máximo | Rango del peso: mediana | Rango: máximo | Rango: medio |
|---|---|---|---|---|---|---|---|---|
| área W = a·A^b | 196 | 40 | 0.978 | 0.83 % | 3.51 % | 7.0 kg | 36.5 kg | 9.6 kg |
| profundidad W = a·D | 196 | 40 | 0.968 | 1.22 % | 4.33 % | 11.2 kg | 42.5 kg | 11.7 kg |

Animal con mayor rango por predictor: área W = a·A^b: fila 1 (Estrellita), 36.5 kg; profundidad W = a·D: fila 30 (Victoria), 42.5 kg.

Detalle por animal en `repetibilidad_3m.csv`.
