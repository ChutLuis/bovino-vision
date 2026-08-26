export type ModelId = 'fp32' | 'w8a32';
export type ArucoBackend = 'js-aruco2';
export type ExportState = 'pending' | 'passed' | 'failed';

export interface Point {
  x: number;
  y: number;
}

export interface LetterboxMeta {
  original_width: number;
  original_height: number;
  scale: number;
  content_width: number;
  content_height: number;
  pad_x: number;
  pad_y: number;
}

export interface DecodedImage {
  width: number;
  height: number;
  rgba: Uint8Array;
}

export interface PreparedImage {
  input: Float32Array;
  letterbox: LetterboxMeta;
}

export interface DeviceInfo {
  brand: string | null;
  manufacturer: string | null;
  model_name: string | null;
  model_id: string | null;
  os_name: string | null;
  os_version: string | null;
  android_api_level: number | null;
  supported_cpu_architectures: string[] | null;
  total_memory_mb: number | null;
  is_physical_device: boolean;
}

export interface InferenceRun {
  device: string;
  foto: string;
  modelo: ModelId;
  phase: 'warmup' | 'measured';
  run: number;
  ms: number;
}

export interface ArucoMeasurement {
  foto: string;
  aruco_ms: number;
  decoded: boolean;
  marker_id: number | null;
  corners: Point[] | null;
  corners_precision: 'pixel';
  subpixel_corners: false;
  marker_side_px: number | null;
  backend: ArucoBackend;
  source_width: number;
  source_height: number;
  working_width: number;
  working_height: number;
}

export interface SegmentationMeasurement {
  foto: string;
  modelo: ModelId;
  cow_dets: number;
  mask_area_px: number;
  postprocess_ms: number;
  selected_confidence: number | null;
  selected_bbox_original_px: [number, number, number, number] | null;
  mask_selection: 'largest_area_cow';
}

export interface TimingStats {
  count: number;
  min_ms: number;
  max_ms: number;
  mean_ms: number;
  p50_ms: number;
  p95_ms: number;
}

export interface BenchmarkSummary {
  fp32: TimingStats;
  w8a32: TimingStats | null;
  aruco_decoded: number;
  aruco_total: number;
  aruco_decode_rate: number;
}

export interface BenchmarkReport {
  schema_version: 1;
  started_at: string;
  finished_at: string;
  device: DeviceInfo;
  app: {
    expo_sdk: string;
    inference_runtime: string;
    inference_delegate: 'cpu-default';
  };
  configuration: {
    input_size: 640;
    input_layout: 'NCHW';
    cow_coco_class: 19;
    confidence_threshold: 0.5;
    warmup_runs_per_photo_model: 1;
    measured_runs_per_photo_model: 5;
    marker_dictionary: 'DICT_6X6_250';
    marker_id: 0;
    marker_size_cm: 15;
    aruco_max_long_side_px: 960;
    mask_area_space: 'original_image_px';
    mask_resample: 'nearest_neighbor_after_letterbox_crop';
  };
  aruco_backend: {
    name: ArucoBackend;
    reason: string;
  };
  inference_runs: InferenceRun[];
  aruco: ArucoMeasurement[];
  segmentation: SegmentationMeasurement[];
  model_failures: Partial<Record<ModelId, string>>;
  summary: BenchmarkSummary;
}

export interface BenchmarkProgress {
  completed: number;
  total: number;
  phase: string;
  photo?: string;
  model?: ModelId;
}

export interface Criterion {
  name: string;
  passed: boolean;
  detail: string;
}

export interface Verdict {
  status: 'GO' | 'NO-GO';
  criteria: Criterion[];
}
