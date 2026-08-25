# Protocolo de campo — Sesión de ampliación de datos (sep 2026)
**Correcciones atendidas: #3 (estadística de muestreo), #5 (pruebas exhaustivas), #7 (mejorar dataset)**
Estado: BORRADOR v0.1 — fecha de sesión pendiente de confirmar con la finca

## Objetivo de la sesión
1. **Censo del hato elegible** (todas las Jersey adultas disponibles, no muestreo por conveniencia).
2. **Ampliar el rango de peso** incorporando novillas y primerizas (categoría registrada como covariable).
3. **Repetibilidad**: 5 fotos por animal para calcular ICC.
4. **Error del instrumento**: doble lectura de cinta bovinométrica por animal.
5. **Set de validación limpio**: fotos destinadas a máscaras dibujadas a mano (corrige el caveat de FINETUNING.md).

## Checklist pre-campo (la semana antes)
- [ ] Confirmar fecha con la finca y transporte (jalón desde el centro de San José Pinula).
- [ ] Imprimir 2 marcadores ArUco ID 0 de 15 cm en PVC (uno de respaldo). Verificar decodificación con `detect_live.py` ANTES de ir.
- [ ] Metro/cinta métrica para verificar los 15 cm impresos (si la impresión salió 14.7 cm, TODA la escala hereda ese error).
- [ ] Cinta bovinométrica (coordinar préstamo con la propietaria).
- [ ] Hojas de bitácora impresas (tabla abajo) + tabla con clip + lapicero de respaldo.
- [ ] Teléfono cargado + batería externa + espacio libre ≥ 5 GB.
- [ ] Poste o soporte para fijar el marcador en el plano del costado del animal.

## Procedimiento por animal (~6–8 min)
1. Leer y anotar el **arete** (y nombre si tiene). Anotar **categoría**: adulta multípara / primeriza / novilla.
2. **Cinta bovinométrica, lectura 1**: perímetro torácico → libras. Anotar.
3. **Cinta, lectura 2** (soltar la cinta y volver a medir, sin ver la lectura 1 — idealmente otra persona). Anotar.
4. Posicionar el animal de lado, marcador fijo en el poste **en el mismo plano del costado**, a 1.5–3 m de la cámara.
5. **5 fotos laterales**: retroceder/acercarse levemente entre tomas (variación natural de distancia). Animal de pie, cuerpo completo + marcador visibles.
6. Verificar en pantalla: ¿marcador nítido? ¿silueta completa? Si no, repetir.
7. Marcar en la bitácora la hora (vincula fotos↔animal por timestamp).

## Bitácora (una fila por animal)
| Arete | Nombre | Categoría | Cinta lb (1) | Cinta lb (2) | Hora fotos | Observaciones |
|---|---|---|---|---|---|---|

## Pruebas adicionales de robustez (últimos 30 min — corrección 5)
Con UN animal dócil, capturar la matriz de estrés del sistema:
- [ ] 3 fotos a contraluz / sombra dura.
- [ ] 3 fotos con ángulo exagerado (~45° en vez de lateral).
- [ ] 3 fotos con el marcador inclinado ~30° respecto al plano.
- [ ] 3 fotos a distancia excesiva (>5 m).
- [ ] 3 fotos con el animal parcialmente ocluido (poste, otra vaca).
Estas fotos NO entran al modelo: alimentan la tabla de casos de fallo y los
mensajes de rechazo del APK (RF-07).

## Exclusiones (idénticas a la tesis, §3.1)
- Gestación avanzada (último tercio) — anotar como excluida, no fotografiar para el modelo.
- Lesiones/edemas visibles que distorsionen la silueta.

## Al volver a casa (mismo día)
- [ ] Respaldar TODAS las fotos sin renombrar a `Thesis_final_raw/raw/sesion_YYYYMMDD/`.
- [ ] Actualizar `MANIFEST.sha1`.
- [ ] Transcribir la bitácora a CSV: `data/field/bitacora_sesion_YYYYMMDD.csv`.
- [ ] Verificación rápida: correr el pipeline sobre 3 fotos para confirmar que el marcador decodifica.
