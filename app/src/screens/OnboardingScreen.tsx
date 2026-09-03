import {
  Image,
  PanResponder,
  Pressable,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useCallback, useMemo, useRef, useState } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { StatusBar } from 'expo-status-bar';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import type { OnboardingScreenProps } from '../navigation/types';
import { BotonPrimario } from '../ui/Botones';
import { MarcaAruco } from '../ui/MarcaAruco';
import { colors, font } from '../ui/theme';

const FOTO_EJEMPLO = require('../../assets/foto-378-limpia.jpg');

// Read by SplashScreen to decide whether the guide still has to be shown (handoff O1).
export const CLAVE_ONBOARDING = 'onboarding_visto';

const UMBRAL_DESLIZAMIENTO = 50;

interface Tarjeta {
  titulo: string;
  cuerpo: string;
}

const TARJETAS: readonly Tarjeta[] = [
  {
    titulo: 'Pese con una foto.',
    cuerpo:
      'Tome una foto de la vaca de lado y Wakx calcula el peso en unos segundos. No necesita señal: todo se hace en el teléfono y las fotos se quedan aquí.',
  },
  {
    titulo: 'El cuadro es la regla.',
    cuerpo:
      'La cámara no sabe qué tan grande es la vaca. El cuadro mide 15 cm y le dice la medida real. Sin cuadro en la foto, no hay peso.',
  },
  {
    titulo: 'De lado y entera.',
    cuerpo:
      'Párese a 2 o 3 pasos, frente al costado. La vaca debe verse de la cabeza a la cola, con el cuadro al lado, derecho y limpio.',
  },
  {
    titulo: 'Listo para pesar.',
    cuerpo:
      'Esta guía aparece solo la primera vez. Si una foto no sirve, Wakx le dirá qué corregir.',
  },
];

const CHECKLIST: readonly { titulo: string; detalle: string }[] = [
  { titulo: 'Vaca entera, de lado', detalle: 'A 2 o 3 pasos de distancia' },
  {
    titulo: 'Cuadro de 15 cm junto al costado',
    detalle: 'Derecho, limpio y sin sombra encima',
  },
  {
    titulo: 'Guarde con el número de arete',
    detalle: 'Así queda en el historial de ese animal',
  },
];

export function OnboardingScreen({ navigation }: OnboardingScreenProps) {
  const insets = useSafeAreaInsets();
  const [paso, setPaso] = useState(0);
  const pasoRef = useRef(0);
  const saliendo = useRef(false);
  pasoRef.current = paso;

  const terminar = useCallback((): void => {
    if (saliendo.current) {
      return;
    }

    saliendo.current = true;
    AsyncStorage.setItem(CLAVE_ONBOARDING, '1')
      .catch((cause: unknown) => {
        // The guide is a courtesy: if the flag cannot be stored, still let the user in.
        console.error('No se pudo guardar la bandera del onboarding.', cause);
      })
      .finally(() => {
        if (navigation.canGoBack()) {
          navigation.goBack();
        } else {
          navigation.replace('Captura');
        }
      });
  }, [navigation]);

  const avanzar = useCallback((): void => {
    if (pasoRef.current >= TARJETAS.length - 1) {
      terminar();
      return;
    }

    setPaso((actual) => Math.min(TARJETAS.length - 1, actual + 1));
  }, [terminar]);

  const retroceder = useCallback((): void => {
    setPaso((actual) => Math.max(0, actual - 1));
  }, []);

  const deslizamiento = useMemo(
    () =>
      PanResponder.create({
        onMoveShouldSetPanResponder: (_evento, gesto) =>
          Math.abs(gesto.dx) > 18 && Math.abs(gesto.dx) > Math.abs(gesto.dy),
        onPanResponderRelease: (_evento, gesto) => {
          if (gesto.dx < -UMBRAL_DESLIZAMIENTO) {
            avanzar();
            return;
          }
          if (gesto.dx > UMBRAL_DESLIZAMIENTO) {
            retroceder();
          }
        },
      }),
    [avanzar, retroceder],
  );

  const tarjeta = TARJETAS[paso];
  const esUltima = paso === TARJETAS.length - 1;

  return (
    <View style={styles.pantalla}>
      <StatusBar style="light" />
      <View style={[styles.cabecera, { paddingTop: insets.top + 14 }]}>
        <Text style={styles.marca}>Wakx</Text>
        {esUltima ? null : (
          <Pressable
            accessibilityLabel="Saltar la guía"
            accessibilityRole="button"
            android_ripple={{ color: colors.rippleSalvia }}
            onPress={terminar}
            style={({ pressed }) => [
              styles.botonSaltar,
              pressed ? styles.presionado : undefined,
            ]}
          >
            <Text style={styles.textoSaltar}>Saltar</Text>
          </Pressable>
        )}
      </View>

      <View style={styles.tarjeta} {...deslizamiento.panHandlers}>
        <View
          style={[
            styles.ilustracion,
            esUltima ? styles.ilustracionLista : styles.ilustracionCentrada,
            paso === 0 ? styles.ilustracionLogo : undefined,
          ]}
        >
          {paso === 0 ? <IlustracionLogo /> : null}
          {paso === 1 ? <IlustracionCuadro /> : null}
          {paso === 2 ? <IlustracionFoto /> : null}
          {esUltima ? <IlustracionChecklist /> : null}
        </View>

        <View style={styles.bloqueTexto}>
          <Text style={styles.overline}>{`Paso ${paso + 1} de ${TARJETAS.length}`}</Text>
          <Text style={styles.titulo}>{tarjeta.titulo}</Text>
          <Text style={styles.cuerpo}>{tarjeta.cuerpo}</Text>
        </View>

        <View style={styles.indicadores}>
          {TARJETAS.map((_tarjeta, indice) => (
            <View
              key={indice}
              style={[
                styles.punto,
                indice === paso ? styles.puntoActivo : styles.puntoInactivo,
              ]}
            />
          ))}
        </View>
      </View>

      <View style={[styles.pie, { paddingBottom: insets.bottom + 16 }]}>
        <BotonPrimario
          titulo={esUltima ? 'Empezar a pesar' : 'Siguiente'}
          onPress={avanzar}
        />
      </View>
    </View>
  );
}

function IlustracionLogo() {
  return (
    <>
      <View style={styles.logoPozo}>
        <MarcaAruco size={72} />
      </View>
      <View style={styles.chips}>
        <Chip conPunto={true} texto="Sin internet" />
        <Chip conPunto={true} texto="Fotos solo en su teléfono" />
      </View>
    </>
  );
}

function IlustracionCuadro() {
  return (
    <>
      <MarcaAruco size={168} borderWidth={14} />
      <View style={styles.cota}>
        <View style={styles.cotaLinea}>
          <View style={styles.cotaTrazo} />
          <View style={[styles.cotaTope, styles.cotaTopeIzquierdo]} />
          <View style={[styles.cotaTope, styles.cotaTopeDerecho]} />
        </View>
        <Text style={styles.cotaTexto}>15 cm</Text>
      </View>
    </>
  );
}

function IlustracionFoto() {
  return (
    <>
      <View style={styles.marcoFoto}>
        <Image
          accessibilityIgnoresInvertColors={true}
          resizeMode="cover"
          source={FOTO_EJEMPLO}
          style={styles.foto}
        />
        <View style={[styles.esquina, styles.esquinaSuperiorIzquierda]} />
        <View style={[styles.esquina, styles.esquinaSuperiorDerecha]} />
        <View style={[styles.esquina, styles.esquinaInferiorIzquierda]} />
        <View style={[styles.esquina, styles.esquinaInferiorDerecha]} />
        <View style={styles.etiquetaFoto}>
          <Text style={styles.etiquetaFotoTexto}>Así se ve una buena foto</Text>
        </View>
      </View>
      <View style={styles.chips}>
        <Chip texto="2 a 3 pasos atrás" />
        <Chip texto="De lado" />
        <Chip texto="Cabeza a cola" />
      </View>
    </>
  );
}

function IlustracionChecklist() {
  return (
    <>
      {CHECKLIST.map((fila) => (
        <View key={fila.titulo} style={styles.fila}>
          <View style={styles.filaCirculo}>
            <Text style={styles.filaCheck}>{'✓'}</Text>
          </View>
          <View style={styles.filaTexto}>
            <Text style={styles.filaTitulo}>{fila.titulo}</Text>
            <Text style={styles.filaDetalle}>{fila.detalle}</Text>
          </View>
        </View>
      ))}
    </>
  );
}

function Chip({ conPunto = false, texto }: { conPunto?: boolean; texto: string }) {
  return (
    <View style={styles.chip}>
      {conPunto ? <View style={styles.chipPunto} /> : null}
      <Text style={styles.chipTexto}>{texto}</Text>
    </View>
  );
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
    minHeight: 44,
    paddingHorizontal: 20,
  },
  marca: {
    color: colors.crema,
    fontFamily: font.black,
    fontSize: 22,
    letterSpacing: -1,
  },
  botonSaltar: {
    minHeight: 44,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 14,
    borderWidth: 1,
    borderColor: colors.salvia,
    borderRadius: 10,
  },
  presionado: {
    opacity: 0.8,
  },
  textoSaltar: {
    color: colors.salviaClara,
    fontFamily: font.bold,
    fontSize: 15,
  },
  tarjeta: {
    flex: 1,
  },
  ilustracion: {
    flex: 1,
    justifyContent: 'center',
    paddingHorizontal: 24,
  },
  ilustracionCentrada: {
    alignItems: 'center',
    gap: 14,
  },
  ilustracionLogo: {
    gap: 22,
  },
  ilustracionLista: {
    gap: 14,
  },
  logoPozo: {
    width: 128,
    height: 128,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 2,
    borderColor: colors.verdeMedio,
    borderRadius: 32,
    backgroundColor: colors.bosquePozo,
  },
  chips: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    gap: 8,
  },
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 7,
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderWidth: 1,
    borderColor: colors.salvia,
    borderRadius: 10,
  },
  chipPunto: {
    width: 7,
    height: 7,
    borderRadius: 4,
    backgroundColor: colors.salvia,
  },
  chipTexto: {
    color: colors.salviaClara,
    fontFamily: font.bold,
    fontSize: 15,
  },
  cota: {
    width: 168,
    alignItems: 'center',
    gap: 6,
  },
  cotaLinea: {
    width: '100%',
    height: 12,
  },
  cotaTrazo: {
    position: 'absolute',
    top: 5,
    right: 0,
    left: 0,
    height: 2,
    backgroundColor: colors.maiz,
  },
  cotaTope: {
    position: 'absolute',
    top: 0,
    width: 2,
    height: 12,
    backgroundColor: colors.maiz,
  },
  cotaTopeIzquierdo: {
    left: 0,
  },
  cotaTopeDerecho: {
    right: 0,
  },
  cotaTexto: {
    color: colors.maiz,
    fontFamily: font.bold,
    fontSize: 16,
  },
  marcoFoto: {
    width: '100%',
    maxWidth: 345,
    aspectRatio: 345 / 234,
    overflow: 'hidden',
    borderRadius: 14,
    backgroundColor: colors.bosqueCamara,
  },
  foto: {
    ...StyleSheet.absoluteFill,
  },
  esquina: {
    position: 'absolute',
    width: 24,
    height: 24,
    borderColor: colors.salviaClara,
  },
  esquinaSuperiorIzquierda: {
    top: 8,
    left: 8,
    borderTopWidth: 3,
    borderLeftWidth: 3,
    borderTopLeftRadius: 6,
  },
  esquinaSuperiorDerecha: {
    top: 8,
    right: 8,
    borderTopWidth: 3,
    borderRightWidth: 3,
    borderTopRightRadius: 6,
  },
  esquinaInferiorIzquierda: {
    bottom: 8,
    left: 8,
    borderBottomWidth: 3,
    borderLeftWidth: 3,
    borderBottomLeftRadius: 6,
  },
  esquinaInferiorDerecha: {
    right: 8,
    bottom: 8,
    borderRightWidth: 3,
    borderBottomWidth: 3,
    borderBottomRightRadius: 6,
  },
  etiquetaFoto: {
    position: 'absolute',
    right: 12,
    bottom: 12,
    paddingVertical: 5,
    paddingHorizontal: 9,
    borderRadius: 8,
    backgroundColor: colors.bosqueEtiqueta,
  },
  etiquetaFotoTexto: {
    color: colors.crema,
    fontFamily: font.bold,
    fontSize: 15,
    lineHeight: 19,
  },
  fila: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: colors.verdeMedio,
  },
  filaCirculo: {
    width: 40,
    height: 40,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 20,
    backgroundColor: colors.maiz,
  },
  filaCheck: {
    color: colors.bosque,
    fontFamily: font.black,
    fontSize: 20,
  },
  filaTexto: {
    flex: 1,
    minWidth: 0,
  },
  filaTitulo: {
    color: colors.crema,
    fontFamily: font.bold,
    fontSize: 18,
    lineHeight: 22,
  },
  filaDetalle: {
    marginTop: 2,
    color: colors.textoClaroSec,
    fontFamily: font.regular,
    fontSize: 15,
    lineHeight: 20,
  },
  bloqueTexto: {
    paddingBottom: 20,
    paddingHorizontal: 24,
  },
  overline: {
    color: colors.maiz,
    fontFamily: font.bold,
    fontSize: 15,
    letterSpacing: 1.5,
    textTransform: 'uppercase',
  },
  titulo: {
    marginTop: 8,
    color: colors.crema,
    fontFamily: font.black,
    fontSize: 34,
    letterSpacing: -1.4,
    lineHeight: 38,
  },
  cuerpo: {
    marginTop: 12,
    color: colors.textoClaroSec,
    fontFamily: font.regular,
    fontSize: 18,
    lineHeight: 26,
  },
  indicadores: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 6,
    paddingBottom: 14,
  },
  punto: {
    height: 8,
    borderRadius: 4,
  },
  puntoActivo: {
    width: 24,
    backgroundColor: colors.maiz,
  },
  puntoInactivo: {
    width: 8,
    backgroundColor: colors.verdeMedio,
  },
  pie: {
    paddingTop: 12,
    paddingHorizontal: 20,
    borderTopWidth: 1,
    borderTopColor: colors.verdeMedio,
    backgroundColor: colors.bosqueProfundo,
  },
});
