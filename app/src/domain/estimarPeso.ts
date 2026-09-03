import type { TfliteModel } from 'react-native-fast-tflite';

import { calcularPeso, type ModeloPeso } from '../estimation/weightModel';
import { detectAruco } from '../vision/aruco';
import { asArrayBuffer, decodeJpegUri, letterboxToNchw, normalizeExifOrientation } from '../vision/image';
import { calcularAreaCm2 } from '../vision/morphometry';
import { measureSegmentation } from '../vision/segment';
import type { EtapaProcesamiento, FotoEntrada, ResultadoEstimacion } from './types';

export interface DependenciasEstimacion {
  modelo_segmentacion: TfliteModel;
  modelo_peso: ModeloPeso;
  notificar_etapa?: (etapa: EtapaProcesamiento) => void | Promise<void>;
}

// This layer has no UI, storage, or model-loading side effects. Inputs are injected by the app shell.
export async function estimarPeso(
  foto: FotoEntrada,
  dependencias: DependenciasEstimacion,
): Promise<ResultadoEstimacion> {
  await dependencias.notificar_etapa?.('buscando_animal');
  const decoded = normalizeExifOrientation(
    await decodeJpegUri(foto.uri),
    foto.orientacion_exif,
  );
  const preparada = letterboxToNchw(decoded);
  const salidas = await dependencias.modelo_segmentacion.run([
    asArrayBuffer(preparada.input),
  ]);
  const resultadoSegmentacion = measureSegmentation(
    salidas,
    preparada.letterbox,
    foto.uri,
    'fp32',
  );
  const segmentacion = resultadoSegmentacion.medida;

  if (
    segmentacion.cow_dets === 0 ||
    segmentacion.mask_area_px <= 0 ||
    segmentacion.selected_bbox_original_px == null ||
    segmentacion.selected_confidence == null
  ) {
    return { ok: false, foto_uri: foto.uri, causa: 'sin_vaca', origen: foto.origen };
  }

  await dependencias.notificar_etapa?.('leyendo_marcador');
  const marcador = detectAruco(decoded);

  // The animal was located before the square was read, so the rejection can point
  // at where the square should have been.
  const bboxAnimal = segmentacion.selected_bbox_original_px;

  if (!marcador.decoded || marcador.marker_id !== 0) {
    return {
      ok: false,
      foto_uri: foto.uri,
      causa: 'sin_marcador',
      origen: foto.origen,
      bbox_original_px: bboxAnimal,
    };
  }

  if (marcador.cm_per_px == null || marcador.corners == null || marcador.corners.length !== 4) {
    return {
      ok: false,
      foto_uri: foto.uri,
      causa: 'marcador_ilegible',
      origen: foto.origen,
      bbox_original_px: bboxAnimal,
    };
  }

  await dependencias.notificar_etapa?.('calculando_peso');
  const areaCm2 = calcularAreaCm2(segmentacion.mask_area_px, marcador.cm_per_px);
  const peso = calcularPeso(areaCm2, dependencias.modelo_peso);

  return {
    ok: true,
    foto_uri: foto.uri,
    peso_kg: peso.peso_kg,
    area_cm2: areaCm2,
    mascara: {
      tipo: 'bbox_placeholder',
      area_px: segmentacion.mask_area_px,
      bbox_original_px: segmentacion.selected_bbox_original_px,
    },
    overlay_mascara: resultadoSegmentacion.overlay_mascara,
    esquinas_marcador: marcador.corners,
    version_modelo: dependencias.modelo_peso.version,
    cm_per_px: marcador.cm_per_px,
    confianza_vaca: segmentacion.selected_confidence,
    intervalo_modelo: peso.intervalo,
  };
}
