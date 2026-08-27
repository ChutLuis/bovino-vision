import { Button, Text, View } from 'react-native';
import { useEffect } from 'react';

import type { SplashScreenProps } from '../navigation/types';
import { usarModelo } from '../providers/ModelProvider';

export function SplashScreen({ navigation }: SplashScreenProps) {
  const { estado, reintentar } = usarModelo();

  useEffect(() => {
    if (estado === 'listo') {
      navigation.replace('Captura');
    }
  }, [estado, navigation]);

  // TODO(diseno): sustituir por logo, fondo y tratamiento de carga de Wakx.
  return (
    <View>
      <Text>Wakx</Text>
      <Text>Estimacion de peso bovino</Text>
      {estado === 'cargando' ? <Text>Preparando la aplicacion...</Text> : null}
      {estado === 'error' ? (
        <>
          <Text>No se pudo preparar la aplicacion. Cierre y vuelva a abrirla.</Text>
          <Button title="Reintentar" onPress={() => void reintentar().catch(() => undefined)} />
        </>
      ) : null}
    </View>
  );
}
