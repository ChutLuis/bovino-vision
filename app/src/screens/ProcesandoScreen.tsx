import { Button, Text, View } from 'react-native';
import { useEffect, useRef, useState } from 'react';

import { estimarPeso } from '../domain/estimarPeso';
import type { EtapaProcesamiento } from '../domain/types';
import type { ProcesandoScreenProps } from '../navigation/types';
import { usarModelo } from '../providers/ModelProvider';

const MENSAJES_ETAPA: Record<EtapaProcesamiento, string> = {
  buscando_animal: 'Buscando al animal…',
  leyendo_marcador: 'Leyendo el marcador…',
  calculando_peso: 'Calculando peso…',
};

export function ProcesandoScreen({ navigation, route }: ProcesandoScreenProps) {
  const { modelo_segmentacion, modelo_peso } = usarModelo();
  const [etapa, setEtapa] = useState<EtapaProcesamiento>('buscando_animal');
  const [error, setError] = useState<string | null>(null);
  const iniciado = useRef(false);

  useEffect(() => {
    if (iniciado.current || modelo_segmentacion == null || modelo_peso == null) {
      return;
    }

    iniciado.current = true;
    let activa = true;

    const actualizarEtapa = async (siguienteEtapa: EtapaProcesamiento): Promise<void> => {
      if (activa) {
        setEtapa(siguienteEtapa);
        await esperarPintado();
      }
    };

    void estimarPeso(route.params.foto, {
      modelo_segmentacion,
      modelo_peso,
      notificar_etapa: actualizarEtapa,
    })
      .then((resultado) => {
        if (activa) {
          navigation.replace('Resultado', { resultado });
        }
      })
      .catch((cause: unknown) => {
        if (activa) {
          setError(cause instanceof Error ? cause.message : String(cause));
        }
      });

    return () => {
      activa = false;
    };
  }, [modelo_segmentacion, modelo_peso, navigation, route.params.foto]);

  // TODO(diseno): usar la foto como fondo y mostrar progreso sin revelar jerga tecnica.
  return (
    <View>
      <Text>Procesando</Text>
      <Text>{MENSAJES_ETAPA[etapa]}</Text>
      <Text>Foto: {route.params.foto.uri}</Text>
      {error != null ? (
        <>
          <Text>No se pudo procesar esta foto.</Text>
          <Text>{error}</Text>
          <Button title="Volver a tomar" onPress={() => navigation.popToTop()} />
        </>
      ) : null}
    </View>
  );
}

function esperarPintado(): Promise<void> {
  return new Promise((resolve) => {
    requestAnimationFrame(() => requestAnimationFrame(() => resolve()));
  });
}
