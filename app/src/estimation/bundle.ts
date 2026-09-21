import { validarIntervalo } from './interval';
import goldenCasesJson from '../../assets/model_bundle/golden_cases.json';
import weightModelJson from '../../assets/model_bundle/weight_model.json';

export interface ModeloPesoBundle {
  a: number;
  b: number;
  interval: unknown | null;
  version: string;
  fuente: string;
}

export interface CasoGoldenPeso {
  foto: string;
  area_cm2: number;
  peso_esperado_kg: number;
  limite_inferior_kg?: number;
  limite_superior_kg?: number;
}

export interface GoldenCasesBundle {
  modelo: string;
  a: number;
  b: number;
  tolerancia_kg: number;
  fuente: string;
  casos: CasoGoldenPeso[];
}

export function cargarBundleModeloPeso(): ModeloPesoBundle {
  const bundle = weightModelJson as ModeloPesoBundle;
  validarNumeroPositivo(bundle.a, 'a');
  validarNumeroPositivo(bundle.b, 'b');
  validarIntervalo(bundle.interval);

  if (typeof bundle.version !== 'string' || bundle.version.length === 0) {
    throw new Error('El bundle de peso no declara una version valida.');
  }

  return bundle;
}

export function cargarCasosGolden(): GoldenCasesBundle {
  const bundle = goldenCasesJson as GoldenCasesBundle;
  validarNumeroPositivo(bundle.tolerancia_kg, 'tolerancia_kg');

  if (!Array.isArray(bundle.casos) || bundle.casos.length === 0) {
    throw new Error('El bundle golden no contiene casos.');
  }

  for (const caso of bundle.casos) {
    validarNumeroPositivo(caso.area_cm2, `area_cm2 de ${caso.foto}`);
    validarNumeroPositivo(caso.peso_esperado_kg, `peso_esperado_kg de ${caso.foto}`);

    if (caso.limite_inferior_kg !== undefined || caso.limite_superior_kg !== undefined) {
      validarNumeroPositivo(caso.limite_inferior_kg, `limite_inferior_kg de ${caso.foto}`);
      validarNumeroPositivo(caso.limite_superior_kg, `limite_superior_kg de ${caso.foto}`);

      if (caso.limite_superior_kg <= caso.limite_inferior_kg) {
        throw new Error(`El caso golden ${caso.foto} tiene los limites invertidos.`);
      }
    }
  }

  return bundle;
}

function validarNumeroPositivo(value: unknown, field: string): asserts value is number {
  if (typeof value !== 'number' || !Number.isFinite(value) || value <= 0) {
    throw new Error(`El bundle contiene ${field} invalido.`);
  }
}
