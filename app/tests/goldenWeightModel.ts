import { ejecutarGoldenPeso } from '../src/estimation/weightModel';

const informe = ejecutarGoldenPeso();

if (!informe.ok) {
  throw new Error(
    `Golden de peso fallo: ${informe.fallos
      .map((fallo) => `${fallo.foto} (${fallo.diferencia_kg.toFixed(4)} kg)`)
      .join(', ')}`,
  );
}

console.log(
  `Golden de peso aprobado: ${informe.casos_revisados} casos, tolerancia ${informe.tolerancia_kg} kg.`,
);
