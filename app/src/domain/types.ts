import type { MascaraVisual, Point } from '../vision/types';

export type CausaRechazo = 'sin_vaca' | 'sin_marcador' | 'marcador_ilegible';

export type EtapaProcesamiento =
  | 'buscando_animal'
  | 'leyendo_marcador'
  | 'calculando_peso';

export interface FotoEntrada {
  uri: string;
  orientacion_exif?: number | null;
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
  version_modelo: string;
  cm_per_px: number;
  confianza_vaca: number;
  intervalo_modelo: unknown | null;
}

export interface EstimacionRechazada {
  ok: false;
  foto_uri: string;
  causa: CausaRechazo;
}

export type ResultadoEstimacion = EstimacionExitosa | EstimacionRechazada;
