import { Alert, Pressable, StyleSheet, Text, View } from 'react-native';
import { useState } from 'react';
import * as ImagePicker from 'expo-image-picker';
import { StatusBar } from 'expo-status-bar';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import type { FotoEntrada } from '../domain/types';
import type { CapturaScreenProps } from '../navigation/types';
import { BotonPrimario } from '../ui/Botones';
import { MarcaAruco } from '../ui/MarcaAruco';
import { colors, font, radius } from '../ui/theme';

export function CapturaScreen({ navigation }: CapturaScreenProps) {
  const [ocupado, setOcupado] = useState(false);
  const insets = useSafeAreaInsets();

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

  return (
    <View style={styles.pantalla}>
      <StatusBar style="light" />
      <View style={[styles.cabecera, { paddingTop: insets.top + 18 }]}>
        <Text style={styles.marca}>Wakx</Text>
        <View style={styles.sinRed}>
          <View style={styles.puntoSinRed} />
          <Text style={styles.sinRedTexto}>Sin internet</Text>
        </View>
      </View>

      <View style={styles.contenido}>
        <Text style={styles.overline}>Antes de tomar la foto</Text>
        <Text style={styles.titulo}>Foto de lado.</Text>
        <Text style={styles.introduccion}>Tomar foto abre la cámara del teléfono.</Text>

        <View style={styles.requisitos}>
          <Requisito
            detalle="De cabeza a cola, de lado."
            numero="01"
            titulo="Vaca completa"
            visual="vaca"
          />
          <Requisito
            detalle="Junto al costado, derecho y limpio."
            numero="02"
            titulo="Cuadro visible"
            visual="marcador"
          />
        </View>
      </View>

      <View style={[styles.pie, { paddingBottom: insets.bottom + 16 }]}>
        <BotonPrimario
          accessibilityLabel="Tomar foto"
          disabled={ocupado}
          titulo="Tomar foto"
          onPress={() => void tomarFoto()}
        />
        <View style={styles.accionesSecundarias}>
          <Pressable
            accessibilityLabel="Elegir foto de la galería"
            accessibilityRole="button"
            android_ripple={{ color: colors.rippleSalvia }}
            disabled={ocupado}
            onPress={() => void elegirGaleria()}
            style={({ pressed }) => [
              styles.accionSecundaria,
              ocupado ? styles.deshabilitado : undefined,
              pressed && !ocupado ? styles.accionPresionada : undefined,
            ]}
          >
            <Text style={styles.accionTexto}>Galería</Text>
          </Pressable>
          <Pressable
            accessibilityLabel="Ver historial"
            accessibilityRole="button"
            android_ripple={{ color: colors.rippleSalvia }}
            disabled={ocupado}
            onPress={() => navigation.navigate('Historial')}
            style={({ pressed }) => [
              styles.accionSecundaria,
              ocupado ? styles.deshabilitado : undefined,
              pressed && !ocupado ? styles.accionPresionada : undefined,
            ]}
          >
            <Text style={styles.accionTexto}>Historial</Text>
          </Pressable>
        </View>
      </View>
    </View>
  );
}

interface RequisitoProps {
  detalle: string;
  numero: string;
  titulo: string;
  visual: 'vaca' | 'marcador';
}

function Requisito({ detalle, numero, titulo, visual }: RequisitoProps) {
  return (
    <View style={styles.requisito}>
      <View style={styles.numeroRequisito}>
        <Text style={styles.numeroRequisitoTexto}>{numero}</Text>
      </View>
      <View style={styles.requisitoTexto}>
        <Text style={styles.requisitoTitulo}>{titulo}</Text>
        <Text style={styles.requisitoDetalle}>{detalle}</Text>
      </View>
      {visual === 'marcador' ? <MarcaAruco size={28} borderWidth={3} /> : <IconoVaca />}
    </View>
  );
}

function IconoVaca() {
  return (
    <View pointerEvents="none" style={styles.iconoVaca}>
      <View style={styles.iconoVacaCuerpo} />
      <View style={styles.iconoVacaCabeza} />
      <View style={styles.iconoVacaPataUno} />
      <View style={styles.iconoVacaPataDos} />
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

const styles = StyleSheet.create({
  pantalla: {
    flex: 1,
    backgroundColor: colors.bosque,
  },
  cabecera: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
  },
  marca: {
    color: colors.crema,
    fontFamily: font.black,
    fontSize: 22,
    letterSpacing: -1,
  },
  sinRed: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  puntoSinRed: {
    width: 7,
    height: 7,
    borderRadius: 4,
    backgroundColor: colors.salvia,
  },
  sinRedTexto: {
    color: colors.salvia,
    fontFamily: font.bold,
    fontSize: 11,
    letterSpacing: 1.2,
    textTransform: 'uppercase',
  },
  contenido: {
    flex: 1,
    paddingTop: 28,
    paddingHorizontal: 20,
  },
  overline: {
    color: colors.maiz,
    fontFamily: font.bold,
    fontSize: 12,
    letterSpacing: 1.5,
    textTransform: 'uppercase',
  },
  titulo: {
    marginTop: 6,
    color: colors.crema,
    fontFamily: font.black,
    fontSize: 32,
    letterSpacing: -1.4,
    lineHeight: 37,
  },
  introduccion: {
    marginTop: 8,
    color: colors.salvia,
    fontFamily: font.regular,
    fontSize: 16,
    lineHeight: 22,
  },
  requisitos: {
    marginTop: 20,
  },
  requisito: {
    flexDirection: 'row',
    alignItems: 'center',
    minHeight: 68,
    gap: 10,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderColor: colors.verdeMedio,
  },
  numeroRequisito: {
    width: 28,
    height: 28,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: colors.maiz,
    borderRadius: 14,
  },
  numeroRequisitoTexto: {
    color: colors.maiz,
    fontFamily: font.bold,
    fontSize: 10,
  },
  requisitoTexto: {
    flex: 1,
    minWidth: 0,
  },
  requisitoTitulo: {
    color: colors.crema,
    fontFamily: font.bold,
    fontSize: 17,
    lineHeight: 21,
  },
  requisitoDetalle: {
    marginTop: 1,
    color: colors.salvia,
    fontFamily: font.regular,
    fontSize: 13,
    lineHeight: 18,
  },
  iconoVaca: {
    width: 36,
    height: 28,
    position: 'relative',
  },
  iconoVacaCuerpo: {
    position: 'absolute',
    bottom: 5,
    left: 0,
    width: 27,
    height: 14,
    borderWidth: 2,
    borderColor: colors.salvia,
    borderRadius: 10,
  },
  iconoVacaCabeza: {
    position: 'absolute',
    right: 0,
    bottom: 10,
    width: 11,
    height: 10,
    borderWidth: 2,
    borderColor: colors.salvia,
    borderRadius: 6,
  },
  iconoVacaPataUno: {
    position: 'absolute',
    bottom: 0,
    left: 8,
    width: 2,
    height: 7,
    backgroundColor: colors.salvia,
  },
  iconoVacaPataDos: {
    position: 'absolute',
    bottom: 0,
    left: 21,
    width: 2,
    height: 7,
    backgroundColor: colors.salvia,
  },
  pie: {
    gap: 10,
    paddingTop: 12,
    paddingHorizontal: 20,
    borderTopWidth: 1,
    borderTopColor: colors.verdeMedio,
    backgroundColor: colors.bosqueProfundo,
  },
  accionesSecundarias: {
    flexDirection: 'row',
    gap: 10,
  },
  accionSecundaria: {
    flex: 1,
    minHeight: 56,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 2,
    borderColor: colors.salvia,
    borderRadius: radius.input,
  },
  accionPresionada: {
    opacity: 0.8,
  },
  accionTexto: {
    color: colors.salvia,
    fontFamily: font.bold,
    fontSize: 16,
  },
  deshabilitado: {
    opacity: 0.5,
  },
});
