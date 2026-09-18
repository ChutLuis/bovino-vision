import type { MascaraVisual, Point } from '../vision/types';

export type CausaRechazo = 'sin_vaca' | 'sin_marcador' | 'marcador_ilegible';

export type EtapaProcesamiento =
  | 'buscando_animal'
  | 'leyendo_marcador'
  | 'calculando_peso';

export type OrigenFoto = 'camara' | 'galeria';

export interface FotoEntrada {
  uri: string;
  orientacion_exif?: number | null;
  origen: OrigenFoto;
}

export interface MascaraDisponible {
  tipo: 'bbox_placeholder';
  area_px: number;
  bbox_original_px: [number, number, number, number];
}

export interface EstimacionExitosa {
  ok: true;
  foto_uri: string;
  peso_kg: number;
  area_cm2: number;
  mascara: MascaraDisponible;
  overlay_mascara: MascaraVisual | null;
  esquinas_marcador: Point[];
  // "peso:<version del bundle de peso>;seg:<sha256[0:16] del .tflite>" (ver vision/modelManifest.ts).
  version_modelo: string;
  cm_per_px: number;
  confianza_vaca: number;
  intervalo_modelo: unknown | null;
}

export interface EstimacionRechazada {
  ok: false;
  foto_uri: string;
  causa: CausaRechazo;
  /** Lets the rejection screen offer a way back to the gallery. */
  origen: OrigenFoto;
  /**
   * Where the animal was found, when it was found at all: the rejection screen
   * marks the missing square next to its flank. Absent for
   * `sin_vaca`, which is precisely the case with no detection.
   */
  bbox_original_px?: [number, number, number, number];
}

export type ResultadoEstimacion = EstimacionExitosa | EstimacionRechazada;
