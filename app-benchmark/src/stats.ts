import type { TimingStats } from './types';

export function timingStats(values: number[]): TimingStats {
  if (values.length === 0) {
    throw new Error('No hay mediciones para calcular estadísticas.');
  }

  const sorted = [...values].sort((left, right) => left - right);
  const total = values.reduce((sum, value) => sum + value, 0);

  return {
    count: values.length,
    min_ms: round(sorted[0]),
    max_ms: round(sorted[sorted.length - 1]),
    mean_ms: round(total / values.length),
    p50_ms: round(percentile(sorted, 0.5)),
    p95_ms: round(percentile(sorted, 0.95)),
  };
}

function percentile(sorted: number[], fraction: number): number {
  const position = (sorted.length - 1) * fraction;
  const lower = Math.floor(position);
  const upper = Math.ceil(position);

  if (lower === upper) {
    return sorted[lower];
  }

  return sorted[lower] + (sorted[upper] - sorted[lower]) * (position - lower);
}

function round(value: number): number {
  return Math.round(value * 1000) / 1000;
}
