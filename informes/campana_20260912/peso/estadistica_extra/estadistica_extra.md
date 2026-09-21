# Estadística complementaria del modelo de peso

| Medida | Valor |
|---|---|
| Animales | 40 |
| MAPE LOO por animal | 7.72 %, IC95 [5.98, 9.57] |
| H1a: MAPE puntual < 10 % / límite superior del IC95 < 10 % | sí / sí |
| a, b del ajuste completo | 2.3410, 0.5347 |
| IC95 bootstrap de b (B = 5000) | [0.326, 0.748] |
| 5-fold agrupado × 2000 | media 7.77 %, sd 0.24, p2.5–p97.5 [7.42, 8.36] |
| 10-fold agrupado × 2000 | media 7.74 %, sd 0.15, p2.5–p97.5 [7.48, 8.06] |
| Predictor medio sin fotografía | 10.23 % |
| Exponente fijo 1.5 / 1.0 / libre | 14.10 / 9.16 / 7.72 % |
| Modelo del piloto (0.375·A^0.706) sin reajuste | MAPE 17.7 %, predicho/real 0.823, subestima 39/40, sd log 0.095 |
| Bland–Altman, predicción LOO − cinta | sesgo -1.5 kg, LoA [-73.1, 70.0] kg; -0.0 %, LoA [-17.4, 21.0] % |
| CCC de Lin / r de Pearson | 0.561 / 0.607 |
| Cobertura del IP95 en LOO | 97.5 % (1 fuera) |
| sd del APE / semianchura aproximada del IC95 | 5.9 pp / ±1.8 pp |
| Cinta de junio, dos lecturas (n = 35) | diferencia absoluta media 3.75 %, máxima 11.9 %; 14.0 kg de media |
| Cambio junio → septiembre (n = 22) | medio +4.0 kg; absoluto medio 4.8 %; sd 5.9 %; rango [-11.5, +11.5] % |

El modelo del piloto se aplica a las mismas fotografías seleccionadas sin reajustar: mide la transferencia entre
protocolos de colocación del marcador, no la calidad del ajuste nuevo. Las dos lecturas de cinta de junio (primera
el día del piloto, segunda el 12 de junio de 2026) incluyen cambio biológico y acotan por arriba el ruido de una
lectura. k-fold con k = n reproduce el LOO: sí. Figuras:
`kfold_repetido.png`, `bland_altman.png`.
