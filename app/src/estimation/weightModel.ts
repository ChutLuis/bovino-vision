import { calcularIntervalo, type IntervaloPeso } from './interval';
import {
  cargarBundleModeloPeso,
  cargarCasosGolden,
  type ModeloPesoBundle,
} from './bundle';

export type ModeloPeso = ModeloPesoBundle;

export interface ResultadoPeso {
  peso_kg: number;
  intervalo: IntervaloPeso | null;
}

export type CampoGoldenPeso = 'peso_kg' | 'limite_inferior_kg' | 'limite_superior_kg';

export interface FalloGoldenPeso {
  foto: string;
  campo: CampoGoldenPeso;
  esperado_kg: number;
  obtenido_kg: number;
  diferencia_kg: number;
}

export interface InformeGoldenPeso {
  ok: boolean;
  casos_revisados: number;
  intervalos_revisados: number;
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

// Cada caso golden fija el peso y, cuando el bundle define intervalo, sus dos
// limites: la app debe reproducir los tres numeros con la misma tolerancia.
export function ejecutarGoldenPeso(): InformeGoldenPeso {
  const modelo = cargarModeloPeso();
  const golden = cargarCasosGolden();
  const fallos: FalloGoldenPeso[] = [];
  let intervalosRevisados = 0;

  const comparar = (foto: string, campo: CampoGoldenPeso, esperado: number, obtenido: number) => {
    const diferencia = Math.abs(obtenido - esperado);

    if (!Number.isFinite(diferencia) || diferencia > golden.tolerancia_kg) {
      fallos.push({ foto, campo, esperado_kg: esperado, obtenido_kg: obtenido, diferencia_kg: diferencia });
    }
  };

  for (const caso of golden.casos) {
    const resultado = calcularPeso(caso.area_cm2, modelo);
    comparar(caso.foto, 'peso_kg', caso.peso_esperado_kg, resultado.peso_kg);

    if (caso.limite_inferior_kg === undefined || caso.limite_superior_kg === undefined) {
      continue;
    }

    intervalosRevisados += 1;
    const inferior = resultado.intervalo?.inferior_kg ?? Number.NaN;
    const superior = resultado.intervalo?.superior_kg ?? Number.NaN;
    comparar(caso.foto, 'limite_inferior_kg', caso.limite_inferior_kg, inferior);
    comparar(caso.foto, 'limite_superior_kg', caso.limite_superior_kg, superior);
  }

  return {
    ok: fallos.length === 0,
    casos_revisados: golden.casos.length,
    intervalos_revisados: intervalosRevisados,
    tolerancia_kg: golden.tolerancia_kg,
    fallos,
  };
}
