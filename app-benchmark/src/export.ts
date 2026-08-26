import * as Sharing from 'expo-sharing';
import { File, Paths } from 'expo-file-system';

import type { BenchmarkReport } from './types';

export async function exportBenchmarkReport(report: BenchmarkReport): Promise<string> {
  const file = new File(Paths.cache, 'benchmark_results.json');
  file.create({ intermediates: true, overwrite: true });
  file.write(JSON.stringify(report, null, 2));

  if (!file.exists) {
    throw new Error('No se pudo crear benchmark_results.json en el cache local.');
  }

  if (!(await Sharing.isAvailableAsync())) {
    throw new Error('El sistema no tiene un intent de compartir disponible.');
  }

  await Sharing.shareAsync(file.uri, {
    dialogTitle: 'Exportar benchmark_results.json',
    mimeType: 'application/json',
    UTI: 'public.json',
  });

  return file.uri;
}
