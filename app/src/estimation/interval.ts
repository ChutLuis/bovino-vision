export interface IntervaloLoglog {
  kind: 'loglog_prediction';
  level: 0.95;
  n: number;
  x_mean: number;
  sxx: number;
  sigma_log: number;
  t_critical: number;
  area_min: number;
  area_max: number;
}
export interface IntervaloPeso {
  nivel: 0.95;
  inferior_kg: number;
  superior_kg: number;
  fuera_de_rango: boolean;
}
export function validarIntervalo(value: unknown): asserts value is IntervaloLoglog | null {
  if (value === null) return;
  if (typeof value !== 'object' || value === undefined) throw new Error('Intervalo del bundle inválido.');
  const v = value as Record<string, unknown>;
  if (v.kind !== 'loglog_prediction' || v.level !== 0.95) throw new Error('Esquema de intervalo no soportado.');
  for (const key of ['n','x_mean','sxx','sigma_log','t_critical','area_min','area_max']) {
    if (typeof v[key] !== 'number' || !Number.isFinite(v[key])) throw new Error(`Intervalo: ${key} inválido.`);
  }
  const i = value as IntervaloLoglog;
  if (!Number.isInteger(i.n) || i.n < 3 || i.sxx <= 0 || i.sigma_log < 0 || i.t_critical <= 0 ||
      i.area_min <= 0 || i.area_max <= i.area_min) throw new Error('Parámetros del intervalo fuera de dominio.');
}
export function calcularIntervalo(area: number, peso: number, interval: unknown): IntervaloPeso | null {
  validarIntervalo(interval);
  if (!Number.isFinite(area) || area <= 0 || !Number.isFinite(peso) || peso <= 0) throw new Error('Área/peso inválido para intervalo.');
  if (interval === null) return null;
  const half = interval.t_critical * interval.sigma_log * Math.sqrt(
    1 + 1 / interval.n + (Math.log(area) - interval.x_mean) ** 2 / interval.sxx,
  );
  const inferior = peso * Math.exp(-half), superior = peso * Math.exp(half);
  if (!Number.isFinite(inferior) || inferior <= 0 || !Number.isFinite(superior)) throw new Error('Intervalo numéricamente fuera de dominio.');
  return {nivel: 0.95, inferior_kg: inferior, superior_kg: superior,
    fuera_de_rango: area < interval.area_min || area > interval.area_max};
}
const KG_POR_LB = 0.45359237;

// Semiancho del intervalo en kilogramos enteros: la mitad de su anchura. El intervalo exacto es asimétrico
// (se construye en escala logarítmica); sus límites quedan en `IntervaloPeso` para quien los necesite.
export function margenKg(value: unknown): number | null {
  if (value == null) return null;
  const v = value as IntervaloPeso;
  if (v.nivel !== 0.95 || !Number.isFinite(v.inferior_kg) || !Number.isFinite(v.superior_kg) ||
      v.inferior_kg <= 0 || v.superior_kg < v.inferior_kg) return null;
  return Math.round((v.superior_kg - v.inferior_kg) / 2);
}
// Texto para la pantalla: un margen simétrico legible en lugar de los límites del intervalo.
export function textoIntervalo(value: unknown): string {
  const margen = margenKg(value);
  if (margen == null) return 'Margen no disponible';
  const fuera = (value as IntervaloPeso).fuera_de_rango ? ' · foto fuera del rango calibrado, el margen puede ser mayor' : '';
  return `Margen ± ${margen} kg${fuera}`;
}
export function textoLibras(pesoKg: number): string {
  return `${Math.round(pesoKg / KG_POR_LB)} lb`;
}
