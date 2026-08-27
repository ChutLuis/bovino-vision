import {
  CONFIDENCE_THRESHOLD,
  COW_COCO_CLASS,
  DETECTION_ROW_SIZE,
  DETECTION_ROWS,
  INPUT_SIZE,
  MASK_CHANNELS,
  MASK_SIZE,
} from './config';
import type {
  LetterboxMeta,
  MascaraVisual,
  MascaraVisualFila,
  SegmentationMeasurement,
} from './types';

interface Candidate {
  offset: number;
  confidence: number;
}

interface ResultadoSegmentacion {
  medida: Omit<SegmentationMeasurement, 'postprocess_ms' | 'cm_per_px' | 'area_cm2'>;
  overlay_mascara: MascaraVisual | null;
}

const MASCARA_VISUAL_COLUMNAS = 64;
const MASCARA_VISUAL_FILAS = 48;

export function measureSegmentation(
  outputBuffers: ArrayBuffer[],
  letterbox: LetterboxMeta,
  foto: string,
  modelo: SegmentationMeasurement['modelo'],
): ResultadoSegmentacion {
  const detections = new Float32Array(outputBuffers[0]);
  const prototypes = new Float32Array(outputBuffers[1]);

  if (
    detections.length !== DETECTION_ROWS * DETECTION_ROW_SIZE ||
    prototypes.length !== MASK_CHANNELS * MASK_SIZE * MASK_SIZE
  ) {
    throw new Error(
      `Longitud de salida inesperada: detecciones=${detections.length}, prototipos=${prototypes.length}.`,
    );
  }

  const candidates = cowCandidates(detections);
  let largestArea = 0;
  let selected: Candidate | null = null;

  for (const candidate of candidates) {
    const area = areaInOriginalPixels(
      detections,
      prototypes,
      candidate.offset,
      letterbox,
    );
    if (selected == null || area > largestArea) {
      largestArea = area;
      selected = candidate;
    }
  }

  return {
    medida: {
      foto,
      modelo,
      cow_dets: candidates.length,
      mask_area_px: largestArea,
      selected_confidence: selected?.confidence ?? null,
      selected_bbox_original_px:
        selected == null
          ? null
          : boxInOriginalPixels(detections, selected.offset, letterbox),
      mask_selection: 'largest_area_cow',
    },
    // The measurement path above stays intact; this second, selected-only pass is visual evidence.
    overlay_mascara:
      selected == null
        ? null
        : construirMascaraVisual(detections, prototypes, selected.offset, letterbox),
  };
}

function cowCandidates(detections: Float32Array): Candidate[] {
  const candidates: Candidate[] = [];

  for (let row = 0; row < DETECTION_ROWS; row += 1) {
    const offset = row * DETECTION_ROW_SIZE;
    const confidence = detections[offset + 4];
    const classId = Math.round(detections[offset + 5]);

    if (
      Number.isFinite(confidence) &&
      confidence >= CONFIDENCE_THRESHOLD &&
      classId === COW_COCO_CLASS
    ) {
      candidates.push({ offset, confidence });
    }
  }

  return candidates;
}

function areaInOriginalPixels(
  detections: Float32Array,
  prototypes: Float32Array,
  detectionOffset: number,
  letterbox: LetterboxMeta,
): number {
  const logits = new Float32Array(MASK_SIZE * MASK_SIZE);
  const coefficientOffset = detectionOffset + 6;

  for (let channel = 0; channel < MASK_CHANNELS; channel += 1) {
    const coefficient = detections[coefficientOffset + channel];
    const prototypeOffset = channel * MASK_SIZE * MASK_SIZE;
    for (let pixel = 0; pixel < logits.length; pixel += 1) {
      logits[pixel] += coefficient * prototypes[prototypeOffset + pixel];
    }
  }

  const x0 = Math.max(0, Math.floor((detections[detectionOffset] * MASK_SIZE) / INPUT_SIZE));
  const y0 = Math.max(0, Math.floor((detections[detectionOffset + 1] * MASK_SIZE) / INPUT_SIZE));
  const x1 = Math.min(
    MASK_SIZE,
    Math.ceil((detections[detectionOffset + 2] * MASK_SIZE) / INPUT_SIZE),
  );
  const y1 = Math.min(
    MASK_SIZE,
    Math.ceil((detections[detectionOffset + 3] * MASK_SIZE) / INPUT_SIZE),
  );
  const prototypeX = new Uint16Array(letterbox.original_width);

  for (let x = 0; x < letterbox.original_width; x += 1) {
    const x640 =
      letterbox.pad_x +
      Math.min(
        letterbox.content_width - 1,
        Math.floor((x * letterbox.content_width) / letterbox.original_width),
      );
    prototypeX[x] = Math.min(MASK_SIZE - 1, Math.floor((x640 * MASK_SIZE) / INPUT_SIZE));
  }

  let area = 0;
  for (let y = 0; y < letterbox.original_height; y += 1) {
    // This is crop(letterbox padding) followed by nearest-neighbor resize to source pixels.
    const y640 =
      letterbox.pad_y +
      Math.min(
        letterbox.content_height - 1,
        Math.floor((y * letterbox.content_height) / letterbox.original_height),
      );
    const prototypeY = Math.min(MASK_SIZE - 1, Math.floor((y640 * MASK_SIZE) / INPUT_SIZE));

    if (prototypeY < y0 || prototypeY >= y1) {
      continue;
    }

    const rowOffset = prototypeY * MASK_SIZE;
    for (let x = 0; x < letterbox.original_width; x += 1) {
      const prototypeColumn = prototypeX[x];
      if (
        prototypeColumn >= x0 &&
        prototypeColumn < x1 &&
        // sigmoid(logit) > 0.5 is equivalent to logit > 0.
        logits[rowOffset + prototypeColumn] > 0
      ) {
        area += 1;
      }
    }
  }

  return area;
}

function construirMascaraVisual(
  detections: Float32Array,
  prototypes: Float32Array,
  detectionOffset: number,
  letterbox: LetterboxMeta,
): MascaraVisual {
  const logits = new Float32Array(MASK_SIZE * MASK_SIZE);
  const coefficientOffset = detectionOffset + 6;

  for (let channel = 0; channel < MASK_CHANNELS; channel += 1) {
    const coefficient = detections[coefficientOffset + channel];
    const prototypeOffset = channel * MASK_SIZE * MASK_SIZE;
    for (let pixel = 0; pixel < logits.length; pixel += 1) {
      logits[pixel] += coefficient * prototypes[prototypeOffset + pixel];
    }
  }

  const x0 = Math.max(0, Math.floor((detections[detectionOffset] * MASK_SIZE) / INPUT_SIZE));
  const y0 = Math.max(0, Math.floor((detections[detectionOffset + 1] * MASK_SIZE) / INPUT_SIZE));
  const x1 = Math.min(
    MASK_SIZE,
    Math.ceil((detections[detectionOffset + 2] * MASK_SIZE) / INPUT_SIZE),
  );
  const y1 = Math.min(
    MASK_SIZE,
    Math.ceil((detections[detectionOffset + 3] * MASK_SIZE) / INPUT_SIZE),
  );
  const filas: MascaraVisualFila[] = [];

  for (let fila = 0; fila < MASCARA_VISUAL_FILAS; fila += 1) {
    const [inicioY, finalY] = rangoPrototipo(
      fila,
      MASCARA_VISUAL_FILAS,
      letterbox.pad_y,
      letterbox.content_height,
    );
    const tramos: Array<[number, number]> = [];
    let inicioTramo: number | null = null;

    for (let columna = 0; columna < MASCARA_VISUAL_COLUMNAS; columna += 1) {
      const [inicioX, finalX] = rangoPrototipo(
        columna,
        MASCARA_VISUAL_COLUMNAS,
        letterbox.pad_x,
        letterbox.content_width,
      );
      const ocupada = bloqueTieneMascara(
        logits,
        inicioX,
        finalX,
        inicioY,
        finalY,
        x0,
        x1,
        y0,
        y1,
      );

      if (ocupada && inicioTramo == null) {
        inicioTramo = columna;
      }

      if (!ocupada && inicioTramo != null) {
        tramos.push([inicioTramo / MASCARA_VISUAL_COLUMNAS, columna / MASCARA_VISUAL_COLUMNAS]);
        inicioTramo = null;
      }
    }

    if (inicioTramo != null) {
      tramos.push([inicioTramo / MASCARA_VISUAL_COLUMNAS, 1]);
    }

    if (tramos.length > 0) {
      filas.push({
        y: fila / MASCARA_VISUAL_FILAS,
        alto: 1 / MASCARA_VISUAL_FILAS,
        tramos,
      });
    }
  }

  return { filas };
}

function rangoPrototipo(
  indice: number,
  total: number,
  padding: number,
  contenido: number,
): [number, number] {
  const inicio640 = padding + (indice * contenido) / total;
  const final640 = padding + ((indice + 1) * contenido) / total;
  return [
    Math.max(0, Math.floor((inicio640 * MASK_SIZE) / INPUT_SIZE)),
    Math.min(MASK_SIZE, Math.ceil((final640 * MASK_SIZE) / INPUT_SIZE)),
  ];
}

function bloqueTieneMascara(
  logits: Float32Array,
  inicioX: number,
  finalX: number,
  inicioY: number,
  finalY: number,
  x0: number,
  x1: number,
  y0: number,
  y1: number,
): boolean {
  const xInicio = Math.max(inicioX, x0);
  const xFinal = Math.min(finalX, x1);
  const yInicio = Math.max(inicioY, y0);
  const yFinal = Math.min(finalY, y1);

  for (let y = yInicio; y < yFinal; y += 1) {
    const rowOffset = y * MASK_SIZE;
    for (let x = xInicio; x < xFinal; x += 1) {
      if (logits[rowOffset + x] > 0) {
        return true;
      }
    }
  }

  return false;
}

function boxInOriginalPixels(
  detections: Float32Array,
  offset: number,
  letterbox: LetterboxMeta,
): [number, number, number, number] {
  const toOriginalX = (value: number) =>
    clamp((value - letterbox.pad_x) / letterbox.scale, 0, letterbox.original_width);
  const toOriginalY = (value: number) =>
    clamp((value - letterbox.pad_y) / letterbox.scale, 0, letterbox.original_height);

  return [
    roundPx(toOriginalX(detections[offset])),
    roundPx(toOriginalY(detections[offset + 1])),
    roundPx(toOriginalX(detections[offset + 2])),
    roundPx(toOriginalY(detections[offset + 3])),
  ];
}

function clamp(value: number, lower: number, upper: number): number {
  return Math.min(upper, Math.max(lower, value));
}

function roundPx(value: number): number {
  return Math.round(value * 100) / 100;
}
