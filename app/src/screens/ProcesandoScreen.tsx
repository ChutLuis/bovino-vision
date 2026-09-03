import {
  Animated,
  Easing,
  Image,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useEffect, useRef, useState } from 'react';
import { StatusBar } from 'expo-status-bar';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { estimarPeso } from '../domain/estimarPeso';
import type { EtapaProcesamiento } from '../domain/types';
import type { ProcesandoScreenProps } from '../navigation/types';
import { usarModelo } from '../providers/ModelProvider';
import { BotonPrimario } from '../ui/Botones';
import { MarcaAruco } from '../ui/MarcaAruco';
import { colors, font, radius } from '../ui/theme';

const MENSAJES_ETAPA: Record<EtapaProcesamiento, string> = {
  buscando_animal: 'Buscando al animal…',
  leyendo_marcador: 'Leyendo el marcador…',
  calculando_peso: 'Calculando peso…',
};

const ETAPAS = Object.keys(MENSAJES_ETAPA) as EtapaProcesamiento[];

export function ProcesandoScreen({ navigation, route }: ProcesandoScreenProps) {
  const { modelo_segmentacion, modelo_peso } = usarModelo();
  const insets = useSafeAreaInsets();
  const [etapa, setEtapa] = useState<EtapaProcesamiento>('buscando_animal');
  const [error, setError] = useState<string | null>(null);
  const iniciado = useRef(false);
  const pulso = useRef(new Animated.Value(1)).current;

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
          console.error('No se pudo procesar la foto.', cause);
          setError(cause instanceof Error ? cause.message : String(cause));
        }
      });

    return () => {
      activa = false;
    };
  }, [modelo_segmentacion, modelo_peso, navigation, route.params.foto]);

  useEffect(() => {
    const animacion = Animated.loop(
      Animated.sequence([
        Animated.timing(pulso, {
          toValue: 0.86,
          duration: 800,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true,
        }),
        Animated.timing(pulso, {
          toValue: 1,
          duration: 800,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true,
        }),
      ]),
    );

    animacion.start();
    return () => animacion.stop();
  }, [pulso]);

  const indiceActivo = Math.max(0, ETAPAS.indexOf(etapa));
  const opacidadPulso = pulso.interpolate({
    inputRange: [0.86, 1],
    outputRange: [0.45, 1],
  });

  return (
    <View style={styles.pantalla}>
      <StatusBar style="light" />
      <Image source={{ uri: route.params.foto.uri }} resizeMode="cover" style={styles.fotoFondo} />
      <View pointerEvents="none" style={styles.overlay} />

      {error != null ? (
        <View
          style={[
            styles.errorEstado,
            { paddingTop: insets.top + 32, paddingBottom: insets.bottom + 24 },
          ]}
        >
          <View style={styles.errorIcono}>
            <Text style={styles.errorSigno}>!</Text>
          </View>
          <Text style={styles.errorTitulo}>No se pudo procesar esta foto.</Text>
          <Text style={styles.errorDetalle}>
            Vuelva a tomar la foto. Si el problema continúa, cierre y abra la aplicación.
          </Text>
          <BotonPrimario titulo="Volver a tomar" onPress={() => navigation.popToTop()} />
        </View>
      ) : (
        <>
          <View style={[styles.cabecera, { top: insets.top + 20 }]}>
            <Text style={styles.overline}>Foto tomada</Text>
            <Text style={styles.titulo}>Revisando la foto.</Text>
          </View>
          <View style={[styles.dock, { paddingBottom: insets.bottom + 10 }]}>
            <View style={styles.dockEncabezado}>
              <Animated.View
                style={{ opacity: opacidadPulso, transform: [{ scale: pulso }] }}
              >
                <MarcaAruco size={32} borderWidth={3} />
              </Animated.View>
              <View style={styles.dockTitulo}>
                <Text style={styles.pasoActual}>{`Paso ${indiceActivo + 1} de ${ETAPAS.length}`}</Text>
                <Text style={styles.dockEstado}>Procesando la foto</Text>
              </View>
            </View>
            <View style={styles.etapas}>
              {ETAPAS.map((etapaActual, index) => {
                const hecha = index < indiceActivo;
                const activa = index === indiceActivo;
                return (
                  <View
                    key={etapaActual}
                    style={[
                      styles.filaEtapa,
                      hecha ? styles.etapaHecha : undefined,
                      !hecha && !activa ? styles.etapaPendiente : undefined,
                    ]}
                  >
                    <Animated.View
                      style={[
                        styles.indicadorEtapa,
                        hecha ? styles.indicadorHecho : undefined,
                        activa
                          ? { opacity: opacidadPulso, transform: [{ scale: pulso }] }
                          : undefined,
                      ]}
                    >
                      {hecha ? <Text style={styles.check}>{'\u2713'}</Text> : <Text style={styles.indiceEtapa}>{index + 1}</Text>}
                    </Animated.View>
                    <Text style={[styles.textoEtapa, activa ? styles.textoEtapaActiva : undefined]}>
                      {MENSAJES_ETAPA[etapaActual]}
                    </Text>
                  </View>
                );
              })}
            </View>
            <Text style={styles.nota}>Esto tarda unos segundos. No cierre la aplicación.</Text>
          </View>
        </>
      )}
    </View>
  );
}

function esperarPintado(): Promise<void> {
  return new Promise((resolve) => {
    requestAnimationFrame(() => requestAnimationFrame(() => resolve()));
  });
}

const styles = StyleSheet.create({
  pantalla: {
    flex: 1,
    backgroundColor: colors.bosqueCamara,
  },
  fotoFondo: {
    ...StyleSheet.absoluteFill,
  },
  overlay: {
    ...StyleSheet.absoluteFill,
    backgroundColor: colors.overlayProcesandoLigero,
  },
  cabecera: {
    position: 'absolute',
    right: 22,
    left: 22,
  },
  overline: {
    color: colors.maiz,
    fontFamily: font.bold,
    fontSize: 13,
    letterSpacing: 1.7,
    textTransform: 'uppercase',
  },
  titulo: {
    maxWidth: 220,
    marginTop: 5,
    color: colors.crema,
    fontFamily: font.black,
    fontSize: 32,
    letterSpacing: -1.5,
    lineHeight: 35,
  },
  dock: {
    position: 'absolute',
    right: 0,
    bottom: 0,
    left: 0,
    paddingTop: 12,
    paddingHorizontal: 16,
    borderTopWidth: 1,
    borderTopColor: colors.bordeClaro,
    borderTopLeftRadius: radius.tarjeta,
    borderTopRightRadius: radius.tarjeta,
    backgroundColor: colors.bosqueProfundo,
  },
  dockEncabezado: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  dockTitulo: {
    flex: 1,
  },
  pasoActual: {
    color: colors.maiz,
    fontFamily: font.bold,
    fontSize: 11,
    letterSpacing: 1.2,
    textTransform: 'uppercase',
  },
  dockEstado: {
    marginTop: 1,
    color: colors.crema,
    fontFamily: font.bold,
    fontSize: 16,
  },
  etapas: {
    gap: 0,
    marginTop: 8,
    paddingTop: 6,
    borderTopWidth: 1,
    borderTopColor: colors.bordeClaro,
  },
  filaEtapa: {
    flexDirection: 'row',
    alignItems: 'center',
    minHeight: 30,
    gap: 8,
  },
  etapaHecha: {
    opacity: 0.78,
  },
  etapaPendiente: {
    opacity: 0.46,
  },
  indicadorEtapa: {
    width: 22,
    height: 22,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: colors.crema,
    borderRadius: 11,
  },
  indicadorHecho: {
    borderColor: colors.maiz,
    backgroundColor: colors.maiz,
  },
  check: {
    color: colors.bosque,
    fontFamily: font.black,
    fontSize: 13,
  },
  indiceEtapa: {
    color: colors.crema,
    fontFamily: font.bold,
    fontSize: 10,
  },
  textoEtapa: {
    flex: 1,
    color: colors.textoClaroTer,
    fontFamily: font.medium,
    fontSize: 15,
    lineHeight: 19,
  },
  textoEtapaActiva: {
    color: colors.crema,
    fontFamily: font.bold,
  },
  nota: {
    marginTop: 6,
    color: colors.salviaClara,
    fontFamily: font.regular,
    fontSize: 12,
    lineHeight: 16,
  },
  errorEstado: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 20,
    paddingHorizontal: 28,
    backgroundColor: colors.overlayProcesando,
  },
  errorIcono: {
    width: 76,
    height: 76,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 38,
    backgroundColor: colors.maiz,
  },
  errorSigno: {
    color: colors.bosque,
    fontFamily: font.black,
    fontSize: 46,
  },
  errorTitulo: {
    color: colors.crema,
    fontFamily: font.black,
    fontSize: 28,
    lineHeight: 34,
    textAlign: 'center',
  },
  errorDetalle: {
    color: colors.textoClaroTer,
    fontFamily: font.regular,
    fontSize: 16,
    lineHeight: 23,
    textAlign: 'center',
  },
});
