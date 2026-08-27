import { Alert, Button, Text, View } from 'react-native';
import { useState } from 'react';
import * as ImagePicker from 'expo-image-picker';

import type { FotoEntrada } from '../domain/types';
import type { CapturaScreenProps } from '../navigation/types';

export function CapturaScreen({ navigation }: CapturaScreenProps) {
  const [ocupado, setOcupado] = useState(false);

  const tomarFoto = async (): Promise<void> => {
    if (ocupado) {
      return;
    }

    setOcupado(true);

    try {
      const permiso = await ImagePicker.requestCameraPermissionsAsync();

      if (!permiso.granted) {
        Alert.alert('Permiso requerido', 'Se necesita permiso para usar la camara.');
        return;
      }

      const resultado = await ImagePicker.launchCameraAsync({
        mediaTypes: ['images'],
        allowsEditing: false,
        quality: 1,
        exif: true,
        cameraType: ImagePicker.CameraType.back,
      });
      abrirFoto(resultado);
    } catch (cause) {
      Alert.alert(
        'No se pudo abrir la camara',
        cause instanceof Error ? cause.message : String(cause),
      );
    } finally {
      setOcupado(false);
    }
  };

  const elegirGaleria = async (): Promise<void> => {
    if (ocupado) {
      return;
    }

    setOcupado(true);

    try {
      const permiso = await ImagePicker.requestMediaLibraryPermissionsAsync();

      if (!permiso.granted) {
        Alert.alert('Permiso requerido', 'Se necesita permiso para ver las fotos.');
        return;
      }

      const resultado = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ['images'],
        allowsEditing: false,
        quality: 1,
        exif: true,
      });
      abrirFoto(resultado);
    } catch (cause) {
      Alert.alert(
        'No se pudo abrir la galeria',
        cause instanceof Error ? cause.message : String(cause),
      );
    } finally {
      setOcupado(false);
    }
  };

  const abrirFoto = (resultado: ImagePicker.ImagePickerResult): void => {
    if (resultado.canceled) {
      return;
    }

    const foto = fotoDesdeAsset(resultado.assets[0]);
    navigation.navigate('Procesando', { foto });
  };

  // TODO(diseno): camara de pantalla completa, guia lateral y disparador de 56 px o mayor.
  return (
    <View>
      <Text>Wakx</Text>
      <Text>Estimacion de peso bovino</Text>
      <Text>Tome una foto de lado con el cuadro de referencia visible.</Text>
      <Button title="Tomar foto" disabled={ocupado} onPress={() => void tomarFoto()} />
      <Button title="Elegir de galeria" disabled={ocupado} onPress={() => void elegirGaleria()} />
      <Button title="Ver historial" disabled={ocupado} onPress={() => navigation.navigate('Historial')} />
    </View>
  );
}

function fotoDesdeAsset(asset: ImagePicker.ImagePickerAsset): FotoEntrada {
  const orientacion = Number(asset.exif?.Orientation);

  return {
    uri: asset.uri,
    orientacion_exif: Number.isFinite(orientacion) ? orientacion : null,
  };
}
