import { File, Paths } from 'expo-file-system';
import * as Sharing from 'expo-sharing';

import type { FilaExportacion } from '../db/dao';

export function construirCsv(filas: FilaExportacion[]): string {
  const encabezado = [
    'arete',
    'nombre',
    'categoria',
    'peso_kg',
    'area_cm2',
    'version_modelo',
    'ruta_foto',
    'timestamp',
  ];
  const contenido = filas.map((fila) => [
    fila.arete,
    fila.nombre ?? '',
    fila.categoria ?? '',
    fila.peso_kg,
    fila.area_cm2,
    fila.version_modelo,
    fila.ruta_foto,
    fila.timestamp,
  ]);

  return [encabezado, ...contenido]
    .map((row) => row.map(escaparCsv).join(','))
    .join('\r\n');
}

export async function exportarCsv(filas: FilaExportacion[]): Promise<string> {
  if (!(await Sharing.isAvailableAsync())) {
    throw new Error('Este dispositivo no puede compartir archivos.');
  }

  const archivo = new File(Paths.cache, `wakx-historial-${Date.now()}.csv`);
  archivo.create({ overwrite: true, intermediates: true });
  archivo.write(construirCsv(filas));

  await Sharing.shareAsync(archivo.uri, {
    mimeType: 'text/csv',
    UTI: 'public.comma-separated-values-text',
    dialogTitle: 'Exportar historial Wakx',
  });

  return archivo.uri;
}

function escaparCsv(value: string | number): string {
  const texto = String(value);
  return `"${texto.replaceAll('"', '""')}"`;
}
