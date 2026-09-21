import { ejecutarGoldenPeso } from '../src/estimation/weightModel';

const informe = ejecutarGoldenPeso();

if (!informe.ok) {
  throw new Error(
    `Golden de peso fallo: ${informe.fallos
      .map((fallo) => `${fallo.foto} ${fallo.campo} (${fallo.diferencia_kg.toFixed(4)} kg)`)
      .join(', ')}`,
  );
}

if (informe.intervalos_revisados !== informe.casos_revisados) {
  throw new Error(
    `Golden de peso incompleto: ${informe.intervalos_revisados} de ${informe.casos_revisados} casos declaran intervalo.`,
  );
}

console.log(
  `Golden de peso aprobado: ${informe.casos_revisados} casos de peso e intervalo, tolerancia ${informe.tolerancia_kg} kg.`,
);
