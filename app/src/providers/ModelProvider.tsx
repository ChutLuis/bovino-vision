import { createContext, useContext, useEffect, useRef, useState, type PropsWithChildren } from 'react';
import type { TfliteModel } from 'react-native-fast-tflite';

import { cargarModeloPeso, type ModeloPeso } from '../estimation/weightModel';
import { INPUT_SIZE } from '../vision/config';
import { asArrayBuffer } from '../vision/image';
import { loadBundledModel } from '../vision/tflite';

type EstadoModelo = 'cargando' | 'listo' | 'error';

interface ModeloContextValue {
  estado: EstadoModelo;
  modelo_segmentacion: TfliteModel | null;
  modelo_peso: ModeloPeso | null;
  error: Error | null;
  reintentar: () => Promise<void>;
}

const ModeloContext = createContext<ModeloContextValue | null>(null);
const modelAsset = require('../../assets/model_bundle/yolo26n-seg.tflite');

export function ModeloProvider({ children }: PropsWithChildren) {
  const [estado, setEstado] = useState<EstadoModelo>('cargando');
  const [modeloSegmentacion, setModeloSegmentacion] = useState<TfliteModel | null>(null);
  const [modeloPeso, setModeloPeso] = useState<ModeloPeso | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const cargaActual = useRef<Promise<void> | null>(null);

  const cargar = async (): Promise<void> => {
    if (cargaActual.current != null) {
      return cargaActual.current;
    }

    setEstado('cargando');
    setError(null);
    const carga = (async () => {
      try {
        const peso = cargarModeloPeso();
        const segmentacion = await loadBundledModel(modelAsset);
        await segmentacion.run([entradaDeCalentamiento()]);
        setModeloPeso(peso);
        setModeloSegmentacion(segmentacion);
        setEstado('listo');
      } catch (cause) {
        const nextError = cause instanceof Error ? cause : new Error(String(cause));
        setError(nextError);
        setEstado('error');
        throw nextError;
      } finally {
        cargaActual.current = null;
      }
    })();

    cargaActual.current = carga;
    return carga;
  };

  useEffect(() => {
    void cargar().catch(() => undefined);
  }, []);

  return (
    <ModeloContext.Provider
      value={{
        estado,
        modelo_segmentacion: modeloSegmentacion,
        modelo_peso: modeloPeso,
        error,
        reintentar: cargar,
      }}
    >
      {children}
    </ModeloContext.Provider>
  );
}

export function usarModelo(): ModeloContextValue {
  const value = useContext(ModeloContext);

  if (value == null) {
    throw new Error('usarModelo debe ejecutarse dentro de ModeloProvider.');
  }

  return value;
}

function entradaDeCalentamiento(): ArrayBuffer {
  const input = new Float32Array(INPUT_SIZE * INPUT_SIZE * 3);
  input.fill(114 / 255);
  return asArrayBuffer(input);
}
