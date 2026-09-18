import { Alert, Image, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useEffect, useRef, useState } from 'react';
import * as ImagePicker from 'expo-image-picker';
import { StatusBar } from 'expo-status-bar';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import type { FotoEntrada, OrigenFoto } from '../domain/types';
import type { CapturaScreenProps } from '../navigation/types';
import { BotonPrimario } from '../ui/Botones';
import { MarcaAruco } from '../ui/MarcaAruco';
import { colors, font, radius } from '../ui/theme';

const FOTO_EJEMPLO = require('../../assets/foto-378-limpia.jpg');

export function CapturaScreen({ navigation, route }: CapturaScreenProps) {
  const aretePrellenado = route.params?.aretePrellenado;
  const [ocupado, setOcupado] = useState(false);
  const galeriaAbierta = useRef(false);
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
      abrirFoto(resultado, 'camara');
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
      abrirFoto(resultado, 'galeria');
    } catch (cause) {
      Alert.alert(
        'No se pudo abrir la galeria',
        cause instanceof Error ? cause.message : String(cause),
      );
    } finally {
      setOcupado(false);
    }
  };

  const abrirFoto = (resultado: ImagePicker.ImagePickerResult, origen: OrigenFoto): void => {
    if (resultado.canceled) {
      return;
    }

    const foto = fotoDesdeAsset(resultado.assets[0], origen);
    navigation.navigate('Procesando', { foto, aretePrellenado });
  };

  // Coming back from a rejected gallery photo reopens the gallery, so the user does
  // not have to remember which way they came in.
  useEffect(() => {
    if (route.params?.abrirGaleria !== true) {
      // Releasing the guard here is what lets a second rejection reopen the gallery.
      galeriaAbierta.current = false;
      return;
    }

    if (galeriaAbierta.current) {
      return;
    }

    galeriaAbierta.current = true;
    navigation.setParams({ abrirGaleria: false });
    void elegirGaleria();
  }, [route.params?.abrirGaleria]);

  return (
    <View style={styles.pantalla}>
      <StatusBar style="light" />
      <View style={[styles.cabecera, { paddingTop: insets.top + 18 }]}>
        <Text style={styles.marca}>Wakx</Text>
        <Pressable
          accessibilityLabel="Ver historial"
          accessibilityRole="button"
          android_ripple={{ color: colors.rippleSalvia }}
          disabled={ocupado}
          onPress={() => navigation.navigate('Historial')}
          style={({ pressed }) => [
            styles.botonHistorial,
            ocupado ? styles.deshabilitado : undefined,
            pressed && !ocupado ? styles.accionPresionada : undefined,
          ]}
        >
          <Text style={styles.iconoHistorial}>{'\u2261'}</Text>
          <Text style={styles.textoHistorial}>Historial</Text>
        </Pressable>
      </View>

      <ScrollView
        contentContainerStyle={{ paddingTop: 28, paddingHorizontal: 20, paddingBottom: 16 }}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
        style={styles.contenido}
      >
        <Text style={styles.overline}>Antes de tomar la foto</Text>
        <Text style={styles.titulo}>Foto de lado.</Text>
        <Text style={styles.introduccion}>Tomar foto abre la cámara del teléfono.</Text>

        <View style={styles.requisitos}>
          <Requisito
            detalle="De cabeza a cola, de lado."
            numero="1"
            titulo="Vaca completa"
            visual="vaca"
          />
          <Requisito
            detalle="Junto al costado, derecho y limpio."
            numero="2"
            titulo="Cuadro visible"
            visual="cuadro"
          />
        </View>

        <Pressable
          accessibilityLabel="Ver la guía otra vez"
          accessibilityRole="button"
          android_ripple={{ color: colors.rippleSalvia }}
          onPress={() => navigation.navigate('Onboarding')}
          style={({ pressed }) => [
            styles.enlaceGuia,
            pressed ? styles.accionPresionada : undefined,
          ]}
        >
          <Text style={styles.enlaceGuiaTexto}>Ver la guía otra vez</Text>
        </Pressable>

        <View style={styles.ejemplo}>
          <Image
            accessibilityIgnoresInvertColors={true}
            accessibilityLabel="Ejemplo de una buena foto"
            resizeMode="cover"
            source={FOTO_EJEMPLO}
            style={styles.ejemploFoto}
          />
          <View style={styles.ejemploEtiquetaArriba}>
            <Text style={styles.ejemploTextoArriba}>Así debe verse</Text>
          </View>
          <View style={styles.ejemploEtiquetaAbajo}>
            <MarcaAruco size={16} borderWidth={2} />
            <Text style={styles.ejemploTextoAbajo}>Cuadro a 3–4 m</Text>
          </View>
        </View>
      </ScrollView>

      <View style={[styles.pie, { paddingBottom: insets.bottom + 16 }]}>
        <BotonPrimario
          accessibilityLabel="Tomar foto"
          disabled={ocupado}
          titulo="Tomar foto"
          onPress={() => void tomarFoto()}
        />
        <Pressable
          accessibilityLabel="Elegir una foto de la galería"
          accessibilityRole="button"
          android_ripple={{ color: colors.rippleSalvia }}
          disabled={ocupado}
          onPress={() => void elegirGaleria()}
          style={({ pressed }) => [
            styles.enlaceGaleria,
            ocupado ? styles.deshabilitado : undefined,
            pressed && !ocupado ? styles.accionPresionada : undefined,
          ]}
        >
          <Text style={styles.enlaceGaleriaTexto}>Elegir una foto de la galería</Text>
        </Pressable>
      </View>
    </View>
  );
}

interface RequisitoProps {
  detalle: string;
  numero: string;
  titulo: string;
  visual: 'vaca' | 'cuadro';
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
      {visual === 'cuadro' ? <MarcaAruco size={30} borderWidth={3} /> : <IconoVaca />}
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

function fotoDesdeAsset(asset: ImagePicker.ImagePickerAsset, origen: OrigenFoto): FotoEntrada {
  const orientacion = Number(asset.exif?.Orientation);

  return {
    uri: asset.uri,
    orientacion_exif: Number.isFinite(orientacion) ? orientacion : null,
    origen,
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
  botonHistorial: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    minHeight: 44,
    paddingHorizontal: 14,
    borderWidth: 2,
    borderColor: colors.salvia,
    borderRadius: 12,
  },
  iconoHistorial: {
    color: colors.salviaClara,
    fontFamily: font.bold,
    fontSize: 18,
    lineHeight: 18,
  },
  textoHistorial: {
    color: colors.salviaClara,
    fontFamily: font.bold,
    fontSize: 15,
  },
  contenido: {
    flex: 1,
  },
  overline: {
    color: colors.maiz,
    fontFamily: font.bold,
    fontSize: 15,
    letterSpacing: 1.2,
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
    color: colors.salviaClara,
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
    minHeight: 70,
    gap: 12,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderColor: colors.verdeMedio,
  },
  numeroRequisito: {
    width: 32,
    height: 32,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 16,
    backgroundColor: colors.maiz,
  },
  numeroRequisitoTexto: {
    color: colors.bosque,
    fontFamily: font.black,
    fontSize: 15,
  },
  requisitoTexto: {
    flex: 1,
    minWidth: 0,
  },
  requisitoTitulo: {
    color: colors.crema,
    fontFamily: font.bold,
    fontSize: 18,
    lineHeight: 22,
  },
  requisitoDetalle: {
    marginTop: 2,
    color: colors.textoClaroSec,
    fontFamily: font.regular,
    fontSize: 15,
    lineHeight: 20,
  },
  ejemplo: {
    position: 'relative',
    height: 200,
    marginTop: 16,
    overflow: 'hidden',
    borderRadius: 16,
    backgroundColor: colors.bosqueCamara,
  },
  ejemploFoto: {
    ...StyleSheet.absoluteFill,
  },
  ejemploEtiquetaArriba: {
    position: 'absolute',
    top: 12,
    left: 12,
    paddingVertical: 6,
    paddingHorizontal: 10,
    borderRadius: 8,
    backgroundColor: colors.bosqueEtiqueta,
  },
  ejemploTextoArriba: {
    color: colors.maiz,
    fontFamily: font.bold,
    fontSize: 15,
  },
  ejemploEtiquetaAbajo: {
    position: 'absolute',
    right: 12,
    bottom: 12,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingVertical: 6,
    paddingHorizontal: 10,
    borderRadius: 8,
    backgroundColor: colors.bosqueEtiqueta,
  },
  ejemploTextoAbajo: {
    color: colors.crema,
    fontFamily: font.bold,
    fontSize: 15,
  },
  enlaceGuia: {
    alignSelf: 'flex-start',
    minHeight: 44,
    justifyContent: 'center',
  },
  enlaceGuiaTexto: {
    color: colors.salviaClara,
    fontFamily: font.bold,
    fontSize: 15,
    textDecorationLine: 'underline',
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
  enlaceGaleria: {
    minHeight: 52,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: radius.input,
  },
  enlaceGaleriaTexto: {
    color: colors.salviaClara,
    fontFamily: font.bold,
    fontSize: 16,
    textDecorationLine: 'underline',
  },
  accionPresionada: {
    opacity: 0.8,
  },
  deshabilitado: {
    opacity: 0.7,
  },
});
