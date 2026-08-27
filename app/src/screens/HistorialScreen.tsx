import { Button, Text, View } from 'react-native';
import { useEffect, useState } from 'react';

import {
  listarAnimales,
  listarEstimaciones,
  listarFilasExportacion,
  type AnimalConResumen,
  type Estimacion,
} from '../data/db/dao';
import { exportarCsv } from '../data/export/csv';
import type { HistorialScreenProps } from '../navigation/types';

export function HistorialScreen({ navigation }: HistorialScreenProps) {
  const [animales, setAnimales] = useState<AnimalConResumen[]>([]);
  const [seleccionado, setSeleccionado] = useState<AnimalConResumen | null>(null);
  const [estimaciones, setEstimaciones] = useState<Estimacion[]>([]);
  const [cargando, setCargando] = useState(true);
  const [mensaje, setMensaje] = useState<string | null>(null);

  const cargarAnimales = async (): Promise<void> => {
    setCargando(true);
    setMensaje(null);

    try {
      setAnimales(await listarAnimales());
    } catch (cause) {
      setMensaje(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setCargando(false);
    }
  };

  useEffect(() => {
    void cargarAnimales();
  }, []);

  const seleccionarAnimal = async (animal: AnimalConResumen): Promise<void> => {
    setSeleccionado(animal);
    setMensaje(null);

    try {
      setEstimaciones(await listarEstimaciones(animal.id));
    } catch (cause) {
      setMensaje(cause instanceof Error ? cause.message : String(cause));
    }
  };

  const exportar = async (): Promise<void> => {
    setMensaje(null);

    try {
      await exportarCsv(await listarFilasExportacion());
      setMensaje('Historial listo para compartir.');
    } catch (cause) {
      setMensaje(cause instanceof Error ? cause.message : String(cause));
    }
  };

  // TODO(diseno): lista de alto contraste, filas grandes y accion de exportacion alcanzable.
  if (seleccionado != null) {
    return (
      <View>
        <Text>Arete: {seleccionado.arete}</Text>
        <Text>Nombre: {seleccionado.nombre ?? 'Sin nombre'}</Text>
        {estimaciones.map((estimacion) => (
          <View key={estimacion.id}>
            <Text>{`${Math.round(estimacion.peso_kg)} kg`}</Text>
            <Text>{estimacion.timestamp}</Text>
          </View>
        ))}
        <Button title="Volver al historial" onPress={() => setSeleccionado(null)} />
      </View>
    );
  }

  return (
    <View>
      <Text>Historial</Text>
      {cargando ? <Text>Cargando...</Text> : null}
      {animales.map((animal) => (
        <View key={animal.id}>
          <Text>{`Arete: ${animal.arete}`}</Text>
          <Text>{animal.nombre ?? 'Sin nombre'}</Text>
          <Text>{`Ultimo peso: ${animal.ultimo_peso_kg == null ? 'Sin estimaciones' : `${Math.round(animal.ultimo_peso_kg)} kg`}`}</Text>
          <Button title="Ver estimaciones" onPress={() => void seleccionarAnimal(animal)} />
        </View>
      ))}
      {mensaje != null ? <Text>{mensaje}</Text> : null}
      <Button title="Actualizar" onPress={() => void cargarAnimales()} />
      <Button title="Exportar CSV" onPress={() => void exportar()} />
      <Button title="Nueva estimacion" onPress={() => navigation.popToTop()} />
    </View>
  );
}
