import { MANIFIESTO_SEGMENTADOR } from './modelManifest';

export const INPUT_SIZE = 640;
export const MASK_SIZE = 160;
export const MASK_CHANNELS = 32;
export const DETECTION_ROWS = 300;
export const DETECTION_ROW_SIZE = 38;
// La clase COCO de la vaca y el hash del segmentador salen del manifiesto del modelo desplegado
// (assets/model_bundle/model_manifest.json), no de constantes sueltas.
export const COW_COCO_CLASS: number = MANIFIESTO_SEGMENTADOR.class_id;
export const SEGMENTER_SHA256: string = MANIFIESTO_SEGMENTADOR.sha256;
export const CONFIDENCE_THRESHOLD = 0.5;
export const WARMUP_RUNS = 1;
export const MEASURED_RUNS = 5;
export const MARKER_ID = 0;
export const MARKER_SIZE_CM = 15;
export const ARUCO_DICTIONARY = 'DICT_6X6_250' as const;
export const ARUCO_MAX_HAMMING_DISTANCE = 5;
// null means detect on the source image without a maximum-side resize.
export const ARUCO_MAX_LONG_SIDE_PX = null;
export const SEGMENTATION_GO_P50_MS = 2500;
export const ARUCO_GO_MIN_DECODED = 9;
