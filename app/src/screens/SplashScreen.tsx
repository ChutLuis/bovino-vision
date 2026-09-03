import {
  Animated,
  Easing,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useEffect, useRef } from 'react';
import { Rubik_400Regular } from '@expo-google-fonts/rubik/400Regular';
import { Rubik_500Medium } from '@expo-google-fonts/rubik/500Medium';
import { Rubik_700Bold } from '@expo-google-fonts/rubik/700Bold';
import { Rubik_900Black } from '@expo-google-fonts/rubik/900Black';
import { useFonts } from '@expo-google-fonts/rubik/useFonts';
import { StatusBar } from 'expo-status-bar';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import type { SplashScreenProps } from '../navigation/types';
import { usarModelo } from '../providers/ModelProvider';
import { BotonPrimario } from '../ui/Botones';
import { MarcaAruco } from '../ui/MarcaAruco';
import { colors, font, type } from '../ui/theme';

export function SplashScreen({ navigation }: SplashScreenProps) {
  const { estado, reintentar } = usarModelo();
  const insets = useSafeAreaInsets();
  const [fuentesCargadas, errorFuentes] = useFonts({
    Rubik_400Regular,
    Rubik_500Medium,
    Rubik_700Bold,
    Rubik_900Black,
  });
  const puntos = useRef([
    new Animated.Value(0.25),
    new Animated.Value(0.25),
    new Animated.Value(0.25),
  ]).current;

  useEffect(() => {
    if (estado === 'listo' && (fuentesCargadas || errorFuentes != null)) {
      navigation.replace('Captura');
    }
  }, [estado, errorFuentes, fuentesCargadas, navigation]);

  useEffect(() => {
    const animacion = Animated.loop(
      Animated.sequence([
        Animated.stagger(
          200,
          puntos.map((punto) =>
            Animated.timing(punto, {
              toValue: 1,
              duration: 200,
              easing: Easing.out(Easing.ease),
              useNativeDriver: true,
            }),
          ),
        ),
        Animated.parallel(
          puntos.map((punto) =>
            Animated.timing(punto, {
              toValue: 0.25,
              duration: 200,
              easing: Easing.in(Easing.ease),
              useNativeDriver: true,
            }),
          ),
        ),
        Animated.delay(400),
      ]),
    );

    animacion.start();
    return () => animacion.stop();
  }, [puntos]);

  return (
    <View style={[styles.pantalla, { paddingTop: insets.top, paddingBottom: insets.bottom }]}>
      <StatusBar style="light" />
      <View style={styles.contenido}>
        <View style={styles.logoPozo}>
          <MarcaAruco size={72} />
        </View>
        <Text style={styles.marca}>Wakx</Text>
        <Text style={styles.subtitulo}>Estimación de peso bovino</Text>

        {estado === 'error' ? (
          <View style={styles.errorEstado}>
            <Text style={styles.errorTexto}>
              No se pudo preparar la aplicación. Cierre y vuelva a abrirla.
            </Text>
            <BotonPrimario
              titulo="Reintentar"
              onPress={() => void reintentar().catch(() => undefined)}
            />
          </View>
        ) : (
          <View style={styles.cargaEstado}>
            <View style={styles.puntos}>
              {puntos.map((punto, index) => (
                <Animated.View key={index} style={[styles.punto, { opacity: punto }]} />
              ))}
            </View>
            <Text style={styles.cargaTexto}>Preparando la aplicación…</Text>
          </View>
        )}
      </View>
      <Text style={styles.sinInternet}>Funciona sin internet</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  pantalla: {
    flex: 1,
    paddingHorizontal: 32,
    backgroundColor: colors.bosque,
  },
  contenido: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  logoPozo: {
    width: 128,
    height: 128,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 28,
    borderWidth: 2,
    borderColor: colors.verdeMedio,
    borderRadius: 32,
    backgroundColor: colors.bosquePozo,
  },
  marca: {
    ...type.display,
    color: colors.crema,
    lineHeight: 64,
  },
  subtitulo: {
    marginTop: 12,
    color: colors.salviaClara,
    fontFamily: font.regular,
    fontSize: 21,
    textAlign: 'center',
  },
  cargaEstado: {
    alignItems: 'center',
    marginTop: 64,
  },
  puntos: {
    flexDirection: 'row',
    gap: 10,
  },
  punto: {
    width: 14,
    height: 14,
    borderRadius: 7,
    backgroundColor: colors.maiz,
  },
  cargaTexto: {
    marginTop: 16,
    color: colors.textoClaroSec,
    fontFamily: font.regular,
    fontSize: 18,
  },
  errorEstado: {
    width: '100%',
    alignItems: 'center',
    gap: 20,
    marginTop: 48,
  },
  errorTexto: {
    color: colors.textoClaroSec,
    fontFamily: font.medium,
    fontSize: 18,
    lineHeight: 26,
    textAlign: 'center',
  },
  sinInternet: {
    marginBottom: 56,
    color: colors.salviaClara,
    fontFamily: font.regular,
    fontSize: 15,
    textAlign: 'center',
  },
});
