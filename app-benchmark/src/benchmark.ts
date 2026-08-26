import type { TfliteModel } from 'react-native-fast-tflite';

import { MODELS, PHOTOS, type ModelAsset } from './assets';
import {
  ARUCO_GO_MIN_DECODED,
  ARUCO_DICTIONARY,
  ARUCO_MAX_LONG_SIDE_PX,
  CONFIDENCE_THRESHOLD,
  COW_COCO_CLASS,
  INPUT_SIZE,
  MARKER_ID,
  MARKER_SIZE_CM,
  MEASURED_RUNS,
  W8A32_GO_P50_MS,
  WARMUP_RUNS,
} from './config';
import { detectAruco } from './aruco';
import { collectDeviceInfo, isGalaxyA25 } from './device';
import { asArrayBuffer, decodeBundledJpeg, letterboxToNchw } from './image';
import { measureSegmentation } from './segment';
import { timingStats } from './stats';
import { loadBundledModel } from './tflite';
import type {
  ArucoMeasurement,
  BenchmarkProgress,
  BenchmarkReport,
  Criterion,
  ExportState,
  InferenceRun,
  SegmentationMeasurement,
  Verdict,
} from './types';

interface LoadedModel {
  definition: ModelAsset;
  model: TfliteModel;
}

export async function runBenchmark(
  onProgress: (progress: BenchmarkProgress) => void,
): Promise<BenchmarkReport> {
  const startedAt = new Date().toISOString();
  const device = collectDeviceInfo();
  const loadedModels: LoadedModel[] = [];

  onProgress({
    completed: 0,
    total: PHOTOS.length * (MODELS.length + 1),
    phase: 'Cargando modelos LiteRT',
  });

  for (const definition of MODELS) {
    loadedModels.push({
      definition,
      model: await loadBundledModel(definition.asset),
    });
  }

  const inferenceRuns: InferenceRun[] = [];
  const aruco: ArucoMeasurement[] = [];
  const segmentation: SegmentationMeasurement[] = [];
  const total = PHOTOS.length * (loadedModels.length + 1);
  let completed = 0;

  for (const photo of PHOTOS) {
    onProgress({
      completed,
      total,
      phase: 'Decodificando imagen',
      photo: photo.label,
    });

    const decoded = await decodeBundledJpeg(photo.asset);
    const arucoMeasurement = detectAruco(decoded);
    aruco.push({ ...arucoMeasurement, foto: photo.id });
    completed += 1;
    onProgress({
      completed,
      total,
      phase: 'ArUco completado',
      photo: photo.label,
    });

    const prepared = letterboxToNchw(decoded);
    const input = asArrayBuffer(prepared.input);

    for (const loaded of loadedModels) {
      onProgress({
        completed,
        total,
        phase: 'Segmentando',
        photo: photo.label,
        model: loaded.definition.id,
      });

      for (let run = 0; run < WARMUP_RUNS; run += 1) {
        const started = performance.now();
        loaded.model.runSync([input]);
        inferenceRuns.push({
          device: deviceLabel(device),
          foto: photo.id,
          modelo: loaded.definition.id,
          phase: 'warmup',
          run,
          ms: roundMs(performance.now() - started),
        });
      }

      let outputs: ArrayBuffer[] | null = null;
      for (let run = 1; run <= MEASURED_RUNS; run += 1) {
        const started = performance.now();
        outputs = loaded.model.runSync([input]);
        inferenceRuns.push({
          device: deviceLabel(device),
          foto: photo.id,
          modelo: loaded.definition.id,
          phase: 'measured',
          run,
          ms: roundMs(performance.now() - started),
        });
      }

      if (outputs == null) {
        throw new Error('La inferencia medida no produjo salidas.');
      }

      const postprocessStarted = performance.now();
      const segmentationMeasurement = measureSegmentation(
        outputs,
        prepared.letterbox,
        photo.id,
        loaded.definition.id,
      );
      segmentation.push({
        ...segmentationMeasurement,
        postprocess_ms: roundMs(performance.now() - postprocessStarted),
      });
      completed += 1;
      onProgress({
        completed,
        total,
        phase: 'Modelo completado',
        photo: photo.label,
        model: loaded.definition.id,
      });
      await yieldToUi();
    }
  }

  const measured = inferenceRuns.filter((run) => run.phase === 'measured');
  const arucoDecoded = aruco.filter((result) => result.decoded).length;

  return {
    schema_version: 1,
    started_at: startedAt,
    finished_at: new Date().toISOString(),
    device,
    app: {
      expo_sdk: '57',
      inference_runtime: 'react-native-fast-tflite 3.0.1',
      inference_delegate: 'cpu-default',
    },
    configuration: {
      input_size: INPUT_SIZE,
      input_layout: 'NCHW',
      cow_coco_class: COW_COCO_CLASS,
      confidence_threshold: CONFIDENCE_THRESHOLD,
      warmup_runs_per_photo_model: WARMUP_RUNS,
      measured_runs_per_photo_model: MEASURED_RUNS,
      marker_dictionary: ARUCO_DICTIONARY,
      marker_id: MARKER_ID,
      marker_size_cm: MARKER_SIZE_CM,
      aruco_max_long_side_px: ARUCO_MAX_LONG_SIDE_PX,
      mask_area_space: 'original_image_px',
      mask_resample: 'nearest_neighbor_after_letterbox_crop',
    },
    aruco_backend: {
      name: 'js-aruco2',
      reason:
        'react-native-fast-opencv@1.0.1 no expone aruco/objdetect; se usa js-aruco2 con el diccionario OpenCV 6x6 limitado a 250 IDs.',
    },
    inference_runs: inferenceRuns,
    aruco,
    segmentation,
    summary: {
      fp32: timingStats(
        measured.filter((run) => run.modelo === 'fp32').map((run) => run.ms),
      ),
      w8a32: timingStats(
        measured.filter((run) => run.modelo === 'w8a32').map((run) => run.ms),
      ),
      aruco_decoded: arucoDecoded,
      aruco_total: aruco.length,
      aruco_decode_rate: aruco.length === 0 ? 0 : arucoDecoded / aruco.length,
    },
  };
}

export function evaluateVerdict(
  report: BenchmarkReport,
  exportState: ExportState,
): Verdict {
  const targetDevice = isGalaxyA25(report.device);
  const criteria: Criterion[] = [
    {
      name: 'Dispositivo objetivo',
      passed: targetDevice,
      detail: targetDevice
        ? 'Samsung Galaxy A25 detectado.'
        : `Resultado no válido para GO: se detectó ${deviceLabel(report.device)} en vez de un Galaxy A25.`,
    },
    {
      name: 'Segmentación w8a32 p50',
      passed: report.summary.w8a32.p50_ms <= W8A32_GO_P50_MS,
      detail: `p50 ${report.summary.w8a32.p50_ms.toFixed(1)} ms; límite ${W8A32_GO_P50_MS} ms.`,
    },
    {
      name: 'Decodificación ArUco ID 0',
      passed: report.summary.aruco_decoded >= ARUCO_GO_MIN_DECODED,
      detail: `${report.summary.aruco_decoded}/${report.summary.aruco_total}; mínimo ${ARUCO_GO_MIN_DECODED}/10.`,
    },
    {
      name: 'Exportación JSON',
      passed: exportState === 'passed',
      detail:
        exportState === 'passed'
          ? 'El intent de compartir benchmark_results.json abrió sin error.'
          : exportState === 'failed'
            ? 'La exportación falló.'
            : 'Pendiente: pulse Exportar JSON para validar este criterio.',
    },
  ];

  return {
    status: criteria.every((criterion) => criterion.passed) ? 'GO' : 'NO-GO',
    criteria,
  };
}

function deviceLabel(reportDevice: BenchmarkReport['device']): string {
  return reportDevice.model_name ?? reportDevice.model_id ?? 'dispositivo desconocido';
}

function roundMs(value: number): number {
  return Math.round(value * 1000) / 1000;
}

function yieldToUi(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, 0));
}
