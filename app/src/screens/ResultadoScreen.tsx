import { Button, Text, TextInput, View } from 'react-native';
import { useState } from 'react';

import { guardarAnimal, guardarEstimacion } from '../data/db/dao';
import { eliminarFotoPrivada, guardarFotoPrivada } from '../data/photos';
import type { CausaRechazo, EstimacionExitosa } from '../domain/types';
import type { ResultadoScreenProps } from '../navigation/types';

const MENSAJES_RECHAZO: Record<CausaRechazo, string> = {
  sin_vaca: 'No se ve la vaca completa. Aléjese un poco y tome la foto de lado.',
  sin_marcador: 'No se ve el cuadro de referencia. Revise que esté visible y limpio.',
  marcador_ilegible:
    'El cuadro de referencia se ve borroso o de lado. Póngalo derecho, junto al costado de la vaca.',
};

export function ResultadoScreen({ navigation, route }: ResultadoScreenProps) {
  const { resultado } = route.params;

  if (!resultado.ok) {
    // TODO(diseno): convertir este estado en la pantalla de rechazo P3b.
    return (
      <View>
        <Text>Resultado</Text>
        <Text>{MENSAJES_RECHAZO[resultado.causa]}</Text>
        <Button title="Volver a tomar" onPress={() => navigation.popToTop()} />
      </View>
    );
  }

  return (
    <ResultadoExitoso
      resultado={resultado}
      onRepetir={() => navigation.popToTop()}
      onGuardar={() => navigation.navigate('Historial')}
    />
  );
}

interface ResultadoExitosoProps {
  resultado: EstimacionExitosa;
  onRepetir: () => void;
  onGuardar: () => void;
}

function ResultadoExitoso({ resultado, onRepetir, onGuardar }: ResultadoExitosoProps) {
  const [arete, setArete] = useState('');
  const [nombre, setNombre] = useState('');
  const [categoria, setCategoria] = useState('');
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const guardar = async (): Promise<void> => {
    if (arete.trim().length === 0) {
      setError('Ingrese el arete antes de guardar.');
      return;
    }

    setGuardando(true);
    setError(null);

    let rutaFoto: string | null = null;
    let estimacionGuardada = false;

    try {
      const animal = await guardarAnimal({
        arete,
        nombre,
        categoria,
      });
      rutaFoto = await guardarFotoPrivada(resultado.foto_uri);
      await guardarEstimacion({
        animal_id: animal.id,
        peso_kg: resultado.peso_kg,
        area_cm2: resultado.area_cm2,
        version_modelo: resultado.version_modelo,
        ruta_foto: rutaFoto,
        timestamp: new Date().toISOString(),
      });
      estimacionGuardada = true;
      onGuardar();
    } catch (cause) {
      if (rutaFoto != null && !estimacionGuardada) {
        try {
          eliminarFotoPrivada(rutaFoto);
        } catch {
          // Keep the original persistence error visible if cleanup also fails.
        }
      }
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setGuardando(false);
    }
  };

  // TODO(diseno): foto, mascara verde translúcida y cuadro ArUco sobrepuestos.
  return (
    <View>
      <Text>Resultado</Text>
      <Text>{`${Math.round(resultado.peso_kg)} kg`}</Text>
      <Text>Foto y guia de resultado pendientes de diseno.</Text>
      <TextInput value={arete} onChangeText={setArete} placeholder="Arete" />
      <TextInput value={nombre} onChangeText={setNombre} placeholder="Nombre opcional" />
      <TextInput value={categoria} onChangeText={setCategoria} placeholder="Categoria opcional" />
      {error != null ? <Text>{error}</Text> : null}
      <Button
        title={guardando ? 'Guardando...' : 'Guardar en historial'}
        disabled={guardando}
        onPress={() => void guardar()}
      />
      <Button title="Repetir foto" onPress={onRepetir} />
    </View>
  );
}
