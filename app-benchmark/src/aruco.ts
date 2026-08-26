import {
  ARUCO_DICTIONARY,
  ARUCO_MAX_HAMMING_DISTANCE,
  MARKER_ID,
  MARKER_SIZE_CM,
} from './config';
import type { ArucoMeasurement, DecodedImage, Point } from './types';

type JsArucoCorner = { x: number; y: number };
type JsArucoMarker = { id: number; corners: JsArucoCorner[] };
type JsArucoDetector = {
  detectImage(width: number, height: number, data: Uint8Array): JsArucoMarker[];
};
type JsArucoApi = {
  DICTIONARIES: Record<
    string,
    { nBits: number; tau: number | null; codeList: unknown[] }
  >;
  Detector: new (config: {
    dictionaryName: string;
    maxHammingDistance: number;
  }) => JsArucoDetector;
};

const AR = loadArucoApi();
require('js-aruco2/src/dictionaries/aruco_6x6_1000');

const DICTIONARY_NAME = ARUCO_DICTIONARY;

function loadArucoApi(): JsArucoApi {
  const arucoModule = require('js-aruco2') as { AR?: JsArucoApi };
  const api =
    arucoModule.AR ?? (globalThis as typeof globalThis & { AR?: JsArucoApi }).AR;

  if (api == null) {
    throw new Error('js-aruco2 no registro su API AR.');
  }

  return api;
}

function ensureDictionary(): void {
  if (AR.DICTIONARIES[DICTIONARY_NAME] != null) {
    return;
  }

  const sixBySix1000 = AR.DICTIONARIES.ARUCO_6X6_1000;
  if (sixBySix1000 == null) {
    throw new Error('js-aruco2 no expuso el diccionario ARUCO_6X6_1000.');
  }

  // OpenCV's 250-marker dictionary is the first 250 codes of its 6x6 family.
  AR.DICTIONARIES[DICTIONARY_NAME] = {
    nBits: sixBySix1000.nBits,
    // OpenCV DICT_6X6_250 uses maxCorrectionBits=5.
    tau: ARUCO_MAX_HAMMING_DISTANCE,
    codeList: sixBySix1000.codeList.slice(0, 250),
  };
}

export function detectAruco(image: DecodedImage): ArucoMeasurement {
  ensureDictionary();
  const startedAt = performance.now();
  const detector = new AR.Detector({
    dictionaryName: DICTIONARY_NAME,
    maxHammingDistance: ARUCO_MAX_HAMMING_DISTANCE,
  });
  const marker = detector
    .detectImage(image.width, image.height, image.rgba)
    .find((candidate) => candidate.id === MARKER_ID);
  const elapsedMs = roundMs(performance.now() - startedAt);

  if (marker == null) {
    return {
      foto: '',
      aruco_ms: elapsedMs,
      decoded: false,
      marker_id: null,
      corners: null,
      corners_precision: 'pixel',
      subpixel_corners: false,
      marker_side_px: null,
      cm_per_px: null,
      backend: 'js-aruco2',
      source_width: image.width,
      source_height: image.height,
      working_width: image.width,
      working_height: image.height,
      aruco_working_resolution: {
        width: image.width,
        height: image.height,
      },
    };
  }

  const corners = marker.corners.map((corner) => ({ x: corner.x, y: corner.y }));
  const markerSidePx = averageSideLength(corners);

  return {
    foto: '',
    aruco_ms: elapsedMs,
    decoded: true,
    marker_id: marker.id,
    corners,
    corners_precision: 'pixel',
    subpixel_corners: false,
    marker_side_px: markerSidePx,
    cm_per_px:
      markerSidePx == null || !Number.isFinite(markerSidePx) || markerSidePx <= 0
        ? null
        : MARKER_SIZE_CM / markerSidePx,
    backend: 'js-aruco2',
    source_width: image.width,
    source_height: image.height,
    working_width: image.width,
    working_height: image.height,
    aruco_working_resolution: {
      width: image.width,
      height: image.height,
    },
  };
}

function averageSideLength(corners: Point[]): number | null {
  if (corners.length !== 4) {
    return null;
  }

  let total = 0;
  for (let index = 0; index < corners.length; index += 1) {
    const current = corners[index];
    const next = corners[(index + 1) % corners.length];
    total += Math.hypot(current.x - next.x, current.y - next.y);
  }

  return total / corners.length;
}

function roundMs(value: number): number {
  return Math.round(value * 1000) / 1000;
}
