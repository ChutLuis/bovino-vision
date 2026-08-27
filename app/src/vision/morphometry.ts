export function calcularAreaCm2(maskAreaPx: number, cmPerPx: number): number {
  if (!Number.isFinite(maskAreaPx) || maskAreaPx <= 0) {
    throw new Error('El area de la mascara debe ser positiva.');
  }

  if (!Number.isFinite(cmPerPx) || cmPerPx <= 0) {
    throw new Error('La escala del marcador debe ser positiva.');
  }

  return maskAreaPx * cmPerPx ** 2;
}
