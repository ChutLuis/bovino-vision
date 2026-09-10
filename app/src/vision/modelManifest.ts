import manifestJson from '../../assets/model_bundle/model_manifest.json';

// Ficha del segmentador empaquetado, generada por pipeline/src/make_model_manifest.py a partir del
// .tflite desplegado. pipeline/tests/test_export_contract.py comprueba que coincide con el archivo.
export interface ManifiestoSegmentador {
  model_file: string;
  sha256: string;
  class_id: number;
  class_name: string;
  names: Record<string, string>;
  ultralytics_version: string | null;
  date: string | null;
  input_shape: number[] | null;
  output_shapes: number[][] | null;
}

const SHA256_HEX = /^[0-9a-f]{64}$/;

export function cargarManifiestoSegmentador(): ManifiestoSegmentador {
  const manifiesto = manifestJson as ManifiestoSegmentador;

  if (typeof manifiesto.sha256 !== 'string' || !SHA256_HEX.test(manifiesto.sha256)) {
    throw new Error('El manifiesto del segmentador no declara un sha256 valido.');
  }

  if (!Number.isInteger(manifiesto.class_id) || manifiesto.class_id < 0) {
    throw new Error('El manifiesto del segmentador no declara un class_id valido.');
  }

  const nombre = manifiesto.names[String(manifiesto.class_id)];

  if (nombre !== manifiesto.class_name) {
    throw new Error(
      `El manifiesto asigna la clase ${manifiesto.class_id} a "${nombre}", no a "${manifiesto.class_name}".`,
    );
  }

  return manifiesto;
}

export const MANIFIESTO_SEGMENTADOR = cargarManifiestoSegmentador();

// Identificador corto y estable del segmentador (16 hex del sha256 del .tflite).
export function versionSegmentador(
  manifiesto: ManifiestoSegmentador = MANIFIESTO_SEGMENTADOR,
): string {
  return `seg:${manifiesto.sha256.slice(0, 16)}`;
}

// version_modelo que se guarda con cada estimacion: modelo de peso + segmentador.
// Formato: "peso:<version del bundle de peso>;seg:<sha256[0:16] del .tflite>".
export function componerVersionModelo(
  versionPeso: string,
  manifiesto: ManifiestoSegmentador = MANIFIESTO_SEGMENTADOR,
): string {
  return `peso:${versionPeso};${versionSegmentador(manifiesto)}`;
}
