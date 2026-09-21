import { calcularIntervalo } from './interval';
import {
  cargarBundleModeloPeso,
  cargarCasosGolden,
  type ModeloPesoBundle,
} from './bundle';

export type ModeloPeso = ModeloPesoBundle;

export interface ResultadoPeso {
  peso_kg: number;
  intervalo: unknown | null;
}

export interface FalloGoldenPeso {
  foto: string;
  esperado_kg: number;
  obtenido_kg: number;
  diferencia_kg: number;
}

export interface InformeGoldenPeso {
  ok: boolean;
  casos_revisados: number;
  tolerancia_kg: number;
  fallos: FalloGoldenPeso[];
}

export function cargarModeloPeso(): ModeloPeso {
  return cargarBundleModeloPeso();
}

export function calcularPeso(areaCm2: number, modelo: ModeloPeso): ResultadoPeso {
  if (!Number.isFinite(areaCm2) || areaCm2 <= 0) {
    throw new Error('El area en centimetros cuadrados debe ser positiva.');
  }

  return {
    peso_kg: modelo.a * areaCm2 ** modelo.b,
    intervalo: calcularIntervalo(areaCm2, modelo.a * areaCm2 ** modelo.b, modelo.interval),
  };
}

export function ejecutarGoldenPeso(): InformeGoldenPeso {
  const modelo = cargarModeloPeso();
  const golden = cargarCasosGolden();
  const fallos: FalloGoldenPeso[] = [];

  for (const caso of golden.casos) {
    const obtenido = calcularPeso(caso.area_cm2, modelo).peso_kg;
    const diferencia = Math.abs(obtenido - caso.peso_esperado_kg);

    if (diferencia > golden.tolerancia_kg) {
      fallos.push({
        foto: caso.foto,
        esperado_kg: caso.peso_esperado_kg,
        obtenido_kg: obtenido,
        diferencia_kg: diferencia,
      });
    }
  }

  return {
    ok: fallos.length === 0,
    casos_revisados: golden.casos.length,
    tolerancia_kg: golden.tolerancia_kg,
    fallos,
  };
}
