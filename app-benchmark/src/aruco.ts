import {
  ARUCO_DICTIONARY,
  ARUCO_MAX_HAMMING_DISTANCE,
  ARUCO_MAX_LONG_SIDE_PX,
  MARKER_ID,
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
  const working = resizeRgbaForAruco(image);
  const startedAt = performance.now();
  const detector = new AR.Detector({
    dictionaryName: DICTIONARY_NAME,
    maxHammingDistance: ARUCO_MAX_HAMMING_DISTANCE,
  });
  const marker = detector
    .detectImage(working.width, working.height, working.rgba)
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
      backend: 'js-aruco2',
      source_width: image.width,
      source_height: image.height,
      working_width: working.width,
      working_height: working.height,
    };
  }

  const corners = marker.corners.map((corner) => ({
    x: (corner.x * image.width) / working.width,
    y: (corner.y * image.height) / working.height,
  }));

  return {
    foto: '',
    aruco_ms: elapsedMs,
    decoded: true,
    marker_id: marker.id,
    corners,
    corners_precision: 'pixel',
    subpixel_corners: false,
    marker_side_px: sideLength(corners),
    backend: 'js-aruco2',
    source_width: image.width,
    source_height: image.height,
    working_width: working.width,
    working_height: working.height,
  };
}

function resizeRgbaForAruco(image: DecodedImage): DecodedImage {
  const longestSide = Math.max(image.width, image.height);
  if (longestSide <= ARUCO_MAX_LONG_SIDE_PX) {
    return image;
  }

  const scale = ARUCO_MAX_LONG_SIDE_PX / longestSide;
  const width = Math.max(1, Math.round(image.width * scale));
  const height = Math.max(1, Math.round(image.height * scale));
  const rgba = new Uint8Array(width * height * 4);

  for (let y = 0; y < height; y += 1) {
    const sourceY = Math.min(image.height - 1, Math.floor((y * image.height) / height));
    for (let x = 0; x < width; x += 1) {
      const sourceX = Math.min(image.width - 1, Math.floor((x * image.width) / width));
      const sourceOffset = (sourceY * image.width + sourceX) * 4;
      const targetOffset = (y * width + x) * 4;
      rgba[targetOffset] = image.rgba[sourceOffset];
      rgba[targetOffset + 1] = image.rgba[sourceOffset + 1];
      rgba[targetOffset + 2] = image.rgba[sourceOffset + 2];
      rgba[targetOffset + 3] = image.rgba[sourceOffset + 3];
    }
  }

  return { width, height, rgba };
}

function sideLength(corners: Point[]): number | null {
  if (corners.length !== 4) {
    return null;
  }

  const [first, second] = corners;
  return roundMs(Math.hypot(first.x - second.x, first.y - second.y));
}

function roundMs(value: number): number {
  return Math.round(value * 1000) / 1000;
}
