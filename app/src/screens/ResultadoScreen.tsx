import {
  Image,
  Keyboard,
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
  type LayoutChangeEvent,
} from 'react-native';
import { useEffect, useRef, useState } from 'react';
import { StatusBar } from 'expo-status-bar';
import { useSafeAreaInsets, type EdgeInsets } from 'react-native-safe-area-context';

import {
  guardarAnimal,
  guardarEstimacion,
  listarAnimales,
  type AnimalConResumen,
} from '../data/db/dao';
import { eliminarFotoPrivada, guardarFotoPrivada } from '../data/photos';
import type { CausaRechazo, EstimacionExitosa, EstimacionRechazada } from '../domain/types';
import type { PesadaGuardada, ResultadoScreenProps } from '../navigation/types';
import type { MascaraVisual, Point } from '../vision/types';
import { BotonPrimario, BotonSecundario } from '../ui/Botones';
import { colors, font, radius, type } from '../ui/theme';

const TITULOS_RECHAZO: Record<CausaRechazo, string> = {
  sin_vaca: 'No se ve la vaca completa',
  sin_marcador: 'No se ve el cuadro',
  marcador_ilegible: 'El cuadro no se puede leer',
};

// One paragraph only: the title says what is wrong, this says what to do (handoff X3).
const CONSEJOS_RECHAZO: Record<CausaRechazo, string> = {
  sin_vaca:
    'Camine unos pasos hacia atrás. La vaca debe caber entera en la pantalla, de la cabeza a la cola.',
  sin_marcador:
    'Ponga el cuadro junto al costado de la vaca, sin lodo ni sombra encima, y tome la foto otra vez.',
  marcador_ilegible:
    'Enderece el cuadro para que mire hacia la cámara y sostenga el teléfono firme al disparar.',
};

// What the dotted square marks: where the cuadro should have been (handoff X2).
const ETIQUETAS_ZONA: Record<CausaRechazo, string> = {
  sin_vaca: 'Aquí falta la vaca completa',
  sin_marcador: 'Aquí falta el cuadro',
  marcador_ilegible: 'Aquí está el cuadro, pero no se lee',
};

const LADO_ZONA_RECHAZO = 112;

interface Tamano {
  width: number;
  height: number;
}

interface RectanguloMostrado {
  left: number;
  top: number;
  width: number;
  height: number;
}

interface PuntoMostrado {
  x: number;
  y: number;
}

const GROSOR_ARISTA_MARCADOR = 3;

// The margin describes the method, never this animal: deriving it from the
// weight made a fixed error look like a per-photo measurement (handoff R2).
const MARGEN_HABITUAL_KG = 13;

function margenHabitualKg(intervalo: unknown): number {
  return typeof intervalo === 'number' && Number.isFinite(intervalo) && intervalo > 0
    ? Math.round(intervalo)
    : MARGEN_HABITUAL_KG;
}

export function ResultadoScreen({ navigation, route }: ResultadoScreenProps) {
  const { aretePrellenado, resultado } = route.params;
  const insets = useSafeAreaInsets();

  if (!resultado.ok) {
    return (
      <Rechazo
        insets={insets}
        resultado={resultado}
        onElegirGaleria={() =>
          navigation.navigate('Captura', { aretePrellenado, abrirGaleria: true })
        }
        onVolverATomar={() => navigation.popToTop()}
      />
    );
  }

  return (
    <ResultadoExitoso
      aretePrellenado={aretePrellenado}
      resultado={resultado}
      onRepetir={() => navigation.popToTop()}
      onGuardar={(guardado) => navigation.replace('Historial', { guardado })}
      insetInferior={insets.bottom}
    />
  );
}

interface RechazoProps {
  insets: EdgeInsets;
  resultado: EstimacionRechazada;
  onElegirGaleria: () => void;
  onVolverATomar: () => void;
}

function Rechazo({ insets, resultado, onElegirGaleria, onVolverATomar }: RechazoProps) {
  const [tamanoPantalla, setTamanoPantalla] = useState<Tamano | null>(null);
  const [tamanoOriginal, setTamanoOriginal] = useState<Tamano | null>(null);

  useEffect(() => {
    let vigente = true;

    Image.getSize(
      resultado.foto_uri,
      (width, height) => {
        if (vigente) {
          setTamanoOriginal({ width, height });
        }
      },
      () => {
        if (vigente) {
          // Without the photo size the marked zone falls back to the left side.
          setTamanoOriginal(null);
        }
      },
    );

    return () => {
      vigente = false;
    };
  }, [resultado.foto_uri]);

  const medirPantalla = ({ nativeEvent }: LayoutChangeEvent): void => {
    const { width, height } = nativeEvent.layout;
    setTamanoPantalla((actual) => {
      if (actual?.width === width && actual.height === height) {
        return actual;
      }
      return { width, height };
    });
  };

  const cajaAnimal =
    resultado.bbox_original_px != null && tamanoOriginal != null && tamanoPantalla != null
      ? mapearBbox(resultado.bbox_original_px, tamanoOriginal, tamanoPantalla, 'cover')
      : null;
  const zona = tamanoPantalla == null ? null : posicionZonaRechazo(cajaAnimal, tamanoPantalla);

  return (
    <View onLayout={medirPantalla} style={styles.rechazoPantalla}>
      <StatusBar style="light" />
      <Image source={{ uri: resultado.foto_uri }} resizeMode="cover" style={styles.fotoFondo} />
      <View pointerEvents="none" style={styles.overlayRechazo} />

      <Text style={[styles.rechazoOverline, { top: insets.top + 20 }]}>Su foto</Text>

      {zona != null ? (
        <View pointerEvents="none" style={[styles.zonaRechazo, zona]}>
          <View style={styles.zonaRecuadro} />
          <Text style={styles.zonaEtiqueta}>{ETIQUETAS_ZONA[resultado.causa]}</Text>
        </View>
      ) : null}

      <View style={[styles.rechazoPanel, { paddingBottom: insets.bottom + 16 }]}>
        <View style={styles.rechazoFila}>
          <View style={styles.rechazoIcono}>
            <Text style={styles.rechazoSigno}>!</Text>
          </View>
          <Text style={styles.rechazoTitulo}>{TITULOS_RECHAZO[resultado.causa]}</Text>
        </View>
        <Text style={styles.rechazoConsejo}>{CONSEJOS_RECHAZO[resultado.causa]}</Text>
        <View style={styles.rechazoAcciones}>
          <BotonPrimario alto={66} titulo="Volver a tomar" onPress={onVolverATomar} />
          {resultado.origen === 'galeria' ? (
            <BotonSecundario
              alto={56}
              tamanioTexto={18}
              titulo="Elegir otra foto de la galería"
              onPress={onElegirGaleria}
            />
          ) : null}
        </View>
      </View>
    </View>
  );
}

// Beside the animal when it was detected, left of centre otherwise; always clear of
// the bottom panel (handoff X2).
function posicionZonaRechazo(
  caja: RectanguloMostrado | null,
  contenedor: Tamano,
): { left: number; top: number } {
  const margen = 20;
  const anchoEtiqueta = 200;
  const izquierdaMaxima = Math.max(margen, contenedor.width - anchoEtiqueta - margen);
  const arribaMaxima = Math.max(margen, contenedor.height * 0.55 - LADO_ZONA_RECHAZO);

  if (caja == null) {
    return {
      left: margen * 2,
      top: Math.min(contenedor.height * 0.38 - LADO_ZONA_RECHAZO / 2, arribaMaxima),
    };
  }

  const espacioDerecha = contenedor.width - (caja.left + caja.width);
  const izquierda =
    espacioDerecha >= LADO_ZONA_RECHAZO + margen
      ? caja.left + caja.width + 8
      : caja.left - LADO_ZONA_RECHAZO - 8;

  return {
    left: Math.min(Math.max(margen, izquierda), izquierdaMaxima),
    top: Math.min(Math.max(margen, caja.top + caja.height * 0.55 - LADO_ZONA_RECHAZO / 2), arribaMaxima),
  };
}

interface ResultadoExitosoProps {
  aretePrellenado?: string;
  resultado: EstimacionExitosa;
  onRepetir: () => void;
  onGuardar: (guardado: PesadaGuardada) => void;
  insetInferior: number;
}

function ResultadoExitoso({
  aretePrellenado,
  resultado,
  onRepetir,
  onGuardar,
  insetInferior,
}: ResultadoExitosoProps) {
  const insets = useSafeAreaInsets();
  const [arete, setArete] = useState(aretePrellenado ?? '');
  const [animales, setAnimales] = useState<AnimalConResumen[]>([]);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [areteEnfocado, setAreteEnfocado] = useState(false);
  const [tecladoVisible, setTecladoVisible] = useState(false);
  const [fotoAmpliada, setFotoAmpliada] = useState(false);
  const [tamanoFoto, setTamanoFoto] = useState<Tamano | null>(null);
  const [tamanoOriginal, setTamanoOriginal] = useState<Tamano | null>(null);
  const [marcadoNoDisponible, setMarcadoNoDisponible] = useState(false);
  const areteRef = useRef<TextInput>(null);
  const resultadoScrollRef = useRef<ScrollView>(null);

  const scrollAlFinal = (): void => {
    requestAnimationFrame(() => {
      resultadoScrollRef.current?.scrollToEnd({ animated: true });
    });
    setTimeout(() => {
      resultadoScrollRef.current?.scrollToEnd({ animated: true });
    }, 100);
    setTimeout(() => {
      resultadoScrollRef.current?.scrollToEnd({ animated: true });
    }, 280);
  };

  useEffect(() => {
    const showSub = Keyboard.addListener('keyboardDidShow', () => {
      setTecladoVisible(true);
      scrollAlFinal();
    });

    const hideSub = Keyboard.addListener('keyboardDidHide', () => {
      setTecladoVisible(false);
      setAreteEnfocado(false);
      areteRef.current?.blur();
    });

    return () => {
      showSub.remove();
      hideSub.remove();
    };
  }, []);

  useEffect(() => {
    let vigente = true;
    listarAnimales()
      .then((lista) => {
        if (vigente) {
          setAnimales(lista);
        }
      })
      .catch((cause) => {
        // The tag chips are a shortcut; typing still works if the list fails.
        console.error('No se pudieron cargar los aretes del historial.', cause);
      });

    return () => {
      vigente = false;
    };
  }, []);

  useEffect(() => {
    let vigente = true;
    setTamanoOriginal(null);
    setMarcadoNoDisponible(false);
    // RN and the vision pipeline both use the photo after EXIF orientation is applied.
    Image.getSize(
      resultado.foto_uri,
      (width, height) => {
        if (vigente) {
          setTamanoOriginal({ width, height });
          setMarcadoNoDisponible(false);
        }
      },
      () => {
        if (vigente) {
          setTamanoOriginal(null);
          setMarcadoNoDisponible(true);
        }
      },
    );

    return () => {
      vigente = false;
    };
  }, [resultado.foto_uri]);

  const guardar = async (): Promise<void> => {
    if (arete.trim().length === 0) {
      setError('Ingrese el arete antes de guardar.');
      enfocarArete();
      return;
    }

    setGuardando(true);
    setError(null);

    let rutaFoto: string | null = null;
    let estimacionGuardada = false;

    try {
      const animal = await guardarAnimal({
        arete,
        nombre: null,
        categoria: null,
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
      onGuardar({ arete: arete.trim(), pesoKg: Math.round(resultado.peso_kg) });
    } catch (cause) {
      console.error('No se pudo guardar la pesada.', cause);
      if (rutaFoto != null && !estimacionGuardada) {
        try {
          eliminarFotoPrivada(rutaFoto);
        } catch (cleanupCause) {
          console.error('No se pudo limpiar la foto privada tras un error de guardado.', cleanupCause);
          // Keep the original persistence error in the console if cleanup also fails.
        }
      }
      setError('No se pudo guardar esta pesada. Inténtelo otra vez.');
    } finally {
      setGuardando(false);
    }
  };

  const cajaMascara =
    tamanoFoto != null && tamanoOriginal != null
      ? mapearBbox(resultado.mascara.bbox_original_px, tamanoOriginal, tamanoFoto, 'cover')
      : null;
  const marcoFoto =
    tamanoFoto != null && tamanoOriginal != null
      ? mapearRectangulo(
          { left: 0, top: 0, width: tamanoOriginal.width, height: tamanoOriginal.height },
          tamanoOriginal,
          tamanoFoto,
          'cover',
        )
      : null;
  const esquinasMarcador =
    tamanoFoto != null && tamanoOriginal != null
      ? mapearEsquinasMarcador(resultado.esquinas_marcador, tamanoOriginal, tamanoFoto, 'cover')
      : null;
  const margenKg = margenHabitualKg(resultado.intervalo_modelo);
  const areteNormalizado = arete.trim();
  const puedeGuardar = areteNormalizado.length > 0;
  const aretesSugeridos = animales
    .filter((animal) => animal.arete.startsWith(areteNormalizado))
    .sort((a, b) => (b.ultima_estimacion ?? '').localeCompare(a.ultima_estimacion ?? ''))
    .map((animal) => animal.arete);

  const actualizarTamanoFoto = ({ nativeEvent }: LayoutChangeEvent): void => {
    const { width, height } = nativeEvent.layout;
    setTamanoFoto((actual) => {
      if (actual?.width === width && actual.height === height) {
        return actual;
      }
      return { width, height };
    });
  };

  const actualizarArete = (value: string): void => {
    setArete(value);
    if (error === 'Ingrese el arete antes de guardar.') {
      setError(null);
    }
  };

  const enfocarArete = (): void => {
    areteRef.current?.focus();
    scrollAlFinal();
  };

  const actualizarFocoArete = (enfocado: boolean): void => {
    setAreteEnfocado(enfocado);
    if (enfocado) {
      scrollAlFinal();
    }
  };

  const abrirFotoAmpliada = (): void => {
    Keyboard.dismiss();
    setFotoAmpliada(true);
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      style={styles.resultadoPantalla}
    >
      <StatusBar style="light" />
      {tecladoVisible ? (
        <View style={[styles.barraResumenCompacta, { paddingTop: insets.top + 8 }]}>
          <View style={styles.resumenCompactoInfo}>
            <Text style={styles.resumenCompactoPeso}>
              {`${Math.round(resultado.peso_kg)} kg`}
            </Text>
            <Text style={styles.resumenCompactoPunto}>·</Text>
            <Text style={styles.resumenCompactoMargen}>{`± ${margenKg} kg`}</Text>
          </View>
          <Pressable
            accessibilityLabel="Ocultar el teclado"
            accessibilityRole="button"
            android_ripple={{ color: colors.rippleSalvia }}
            onPress={() => {
              areteRef.current?.blur();
              Keyboard.dismiss();
            }}
            style={({ pressed }) => [
              styles.botonOcultarTeclado,
              pressed ? styles.botonOcultarPresionado : undefined,
            ]}
          >
            <Text style={styles.textoOcultarTeclado}>Listo</Text>
          </Pressable>
        </View>
      ) : null}
      <ScrollView
        contentContainerStyle={[
          styles.resultadoContenido,
          { paddingBottom: tecladoVisible ? 160 : Math.max(32, insetInferior + 24) },
        ]}
        keyboardDismissMode="on-drag"
        keyboardShouldPersistTaps="handled"
        ref={resultadoScrollRef}
        showsVerticalScrollIndicator={false}
        style={styles.resultadoScroll}
      >
        <Pressable
          accessibilityHint="Abre la foto en grande, con la vaca y el cuadro señalados."
          accessibilityLabel="Ver la foto en grande"
          accessibilityRole="button"
          android_ripple={{ color: colors.rippleSalvia }}
          onLayout={actualizarTamanoFoto}
          onPress={abrirFotoAmpliada}
          style={({ pressed }) => [
            styles.fotoResultado,
            pressed ? styles.fotoResultadoPresionada : undefined,
          ]}
        >
          <Image source={{ uri: resultado.foto_uri }} resizeMode="cover" style={styles.fotoFondo} />
          {resultado.overlay_mascara != null && marcoFoto != null ? (
            <MascaraPintada mascara={resultado.overlay_mascara} rectangulo={marcoFoto} />
          ) : null}
          {cajaMascara != null ? <EsquinasFoco rectangulo={cajaMascara} /> : null}
          {esquinasMarcador != null ? <MarcadorArucoLeido esquinas={esquinasMarcador} /> : null}
          {marcadoNoDisponible ? (
            <View pointerEvents="none" style={styles.avisoMarcado}>
              <Text style={styles.avisoMarcadoTexto}>No se pudo señalar la vaca ni el cuadro sobre la foto.</Text>
            </View>
          ) : null}
          <View pointerEvents="none" style={[styles.chipCuadro, { top: insets.top + 12 }]}>
            <Text style={styles.chipCuadroTexto}>{'\u2713 Cuadro leído'}</Text>
          </View>
        </Pressable>

        <View style={styles.panelResultado}>
          <View style={styles.resumenPeso}>
            <Text style={styles.overline}>Peso estimado</Text>
            <View style={styles.filaPeso}>
              <Text style={styles.peso}>{Math.round(resultado.peso_kg)}</Text>
              <Text style={styles.unidad}>kg</Text>
            </View>
            <Text style={styles.margenMetodo}>{`Margen habitual del método: ± ${margenKg} kg`}</Text>
          </View>

          <View style={styles.formulario}>
            <Text style={styles.etiquetaCampo}>Arete del animal</Text>
            <View
              style={[
                styles.campoContenedor,
                areteEnfocado ? styles.campoEnfocado : undefined,
                error === 'Ingrese el arete antes de guardar.' ? styles.campoError : undefined,
              ]}
            >
              <TextInput
                accessibilityLabel="Número de arete del animal"
                autoCapitalize="characters"
                inputMode="numeric"
                keyboardType="numeric"
                maxLength={6}
                onChangeText={actualizarArete}
                onBlur={() => actualizarFocoArete(false)}
                onFocus={() => actualizarFocoArete(true)}
                onPressIn={scrollAlFinal}
                onSubmitEditing={() => void guardar()}
                placeholder="Escriba el arete"
                placeholderTextColor={colors.grisCalido}
                ref={areteRef}
                returnKeyType="done"
                style={styles.campo}
                value={arete}
              />
              <Text style={styles.reglaCampo}>1–6 dígitos</Text>
            </View>
            {aretesSugeridos.length > 0 ? (
              <View style={styles.sugerenciasBloque}>
                <Text style={styles.sugerenciasEtiqueta}>Ya en el historial (toque para usar):</Text>
                <ScrollView
                  contentContainerStyle={styles.sugerenciasFila}
                  horizontal={true}
                  keyboardShouldPersistTaps="handled"
                  showsHorizontalScrollIndicator={false}
                >
                  {aretesSugeridos.map((valor) => (
                    <Pressable
                      accessibilityLabel={`Usar el arete ${valor}`}
                      accessibilityRole="button"
                      android_ripple={{ color: colors.ripplePrimario }}
                      hitSlop={{ bottom: 2, top: 2 }}
                      key={valor}
                      onPress={() => actualizarArete(valor)}
                      style={({ pressed }) => [
                        styles.chipArete,
                        pressed ? styles.chipAretePresionado : undefined,
                      ]}
                    >
                      <Text style={styles.textoChipArete}>{valor}</Text>
                    </Pressable>
                  ))}
                </ScrollView>
              </View>
            ) : null}
            {error != null ? <Text style={styles.errorGuardar}>{error}</Text> : null}
          </View>

          <View style={styles.accionesResultado}>
            <BotonPrimario
              accessibilityLabel="Guardar pesada en el historial"
              alto={56}
              disabled={guardando || !puedeGuardar}
              titulo={guardando ? 'Guardando…' : 'Guardar pesada'}
              onPress={() => void guardar()}
            />
            {!puedeGuardar && !guardando ? (
              <Text style={styles.ayudaGuardar}>Escriba el arete para guardar</Text>
            ) : null}
            <BotonSecundario alto={56} tamanioTexto={20} titulo="Repetir foto" onPress={onRepetir} />
          </View>
        </View>
      </ScrollView>

      <Modal
        animationType="fade"
        onRequestClose={() => setFotoAmpliada(false)}
        visible={fotoAmpliada}
      >
        <FotoAmpliada
          esquinasMarcador={resultado.esquinas_marcador}
          fotoUri={resultado.foto_uri}
          mascara={resultado.overlay_mascara}
          mascaraBbox={resultado.mascara.bbox_original_px}
          onClose={() => setFotoAmpliada(false)}
        />
      </Modal>
    </KeyboardAvoidingView>
  );
}

function EsquinasFoco({ rectangulo }: { rectangulo: RectanguloMostrado }) {
  return (
    <View pointerEvents="none" style={[styles.foco, rectangulo]}>
      <View style={[styles.esquinaFoco, styles.esquinaSuperiorIzquierda]} />
      <View style={[styles.esquinaFoco, styles.esquinaSuperiorDerecha]} />
      <View style={[styles.esquinaFoco, styles.esquinaInferiorIzquierda]} />
      <View style={[styles.esquinaFoco, styles.esquinaInferiorDerecha]} />
    </View>
  );
}

function MascaraPintada({
  mascara,
  rectangulo,
}: {
  mascara: MascaraVisual;
  rectangulo: RectanguloMostrado;
}) {
  return (
    <View pointerEvents="none" style={[styles.mascaraPintada, rectangulo]}>
      {mascara.filas.map((fila, indiceFila) =>
        fila.tramos.map(([inicio, final], indiceTramo) => (
          <View
            key={`${indiceFila}-${indiceTramo}`}
            style={[
              styles.tramoMascara,
              {
                left: inicio * rectangulo.width,
                top: fila.y * rectangulo.height,
                width: (final - inicio) * rectangulo.width,
                height: fila.alto * rectangulo.height,
              },
            ]}
          />
        )),
      )}
    </View>
  );
}

function MarcadorArucoLeido({ esquinas }: { esquinas: PuntoMostrado[] }) {
  return (
    <View pointerEvents="none" style={StyleSheet.absoluteFill}>
      {esquinas.map((esquina, indice) => {
        const siguiente = esquinas[(indice + 1) % esquinas.length];
        const ancho = Math.hypot(siguiente.x - esquina.x, siguiente.y - esquina.y);
        const angulo = (Math.atan2(siguiente.y - esquina.y, siguiente.x - esquina.x) * 180) / Math.PI;

        return (
          <View
            key={`arista-${indice}`}
            style={[
              styles.aristaMarcador,
              {
                left: (esquina.x + siguiente.x - ancho) / 2,
                top: (esquina.y + siguiente.y - GROSOR_ARISTA_MARCADOR) / 2,
                width: ancho,
                transform: [{ rotate: `${angulo}deg` }],
              },
            ]}
          />
        );
      })}
      {esquinas.map((esquina, indice) => (
        <View
          key={`esquina-${indice}`}
          style={[
            styles.esquinaMarcador,
            {
              left: esquina.x - 4,
              top: esquina.y - 4,
            },
          ]}
        />
      ))}
    </View>
  );
}

interface FotoAmpliadaProps {
  esquinasMarcador: Point[];
  fotoUri: string;
  mascara: MascaraVisual | null;
  mascaraBbox: [number, number, number, number];
  onClose: () => void;
}

function FotoAmpliada({
  esquinasMarcador,
  fotoUri,
  mascara,
  mascaraBbox,
  onClose,
}: FotoAmpliadaProps) {
  const insets = useSafeAreaInsets();
  const [tamanoFoto, setTamanoFoto] = useState<Tamano | null>(null);
  const [tamanoOriginal, setTamanoOriginal] = useState<Tamano | null>(null);
  const [marcadoNoDisponible, setMarcadoNoDisponible] = useState(false);

  useEffect(() => {
    let vigente = true;

    Image.getSize(
      fotoUri,
      (width, height) => {
        if (vigente) {
          setTamanoOriginal({ width, height });
          setMarcadoNoDisponible(false);
        }
      },
      () => {
        if (vigente) {
          setTamanoOriginal(null);
          setMarcadoNoDisponible(true);
        }
      },
    );

    return () => {
      vigente = false;
    };
  }, [fotoUri]);

  const actualizarTamanoFoto = ({ nativeEvent }: LayoutChangeEvent): void => {
    const { width, height } = nativeEvent.layout;
    setTamanoFoto((actual) => {
      if (actual?.width === width && actual.height === height) {
        return actual;
      }
      return { width, height };
    });
  };

  const cajaMascara =
    tamanoFoto != null && tamanoOriginal != null
      ? mapearBbox(mascaraBbox, tamanoOriginal, tamanoFoto, 'contain')
      : null;
  const marcoFoto =
    tamanoFoto != null && tamanoOriginal != null
      ? mapearRectangulo(
          { left: 0, top: 0, width: tamanoOriginal.width, height: tamanoOriginal.height },
          tamanoOriginal,
          tamanoFoto,
          'contain',
        )
      : null;
  const esquinas =
    tamanoFoto != null && tamanoOriginal != null
      ? mapearEsquinasMarcador(esquinasMarcador, tamanoOriginal, tamanoFoto, 'contain')
      : null;
  const cajaMarcador = esquinas != null ? rectanguloDesdePuntos(esquinas) : null;
  const posicionEtiqueta =
    cajaMarcador != null && tamanoFoto != null
      ? calcularPosicionEtiquetaMarcador(cajaMarcador, cajaMascara, tamanoFoto)
      : null;

  return (
    <View style={styles.modalFotoPantalla}>
      <StatusBar style="light" />
      <View style={[styles.cabeceraFotoAmpliada, { paddingTop: insets.top + 10 }]}>
        <View style={styles.tituloFotoAmpliada}>
          <Text style={styles.tituloFotoAmpliadaTexto}>Foto con evidencia</Text>
          <Text style={styles.subtituloFotoAmpliada}>Máscara y cuadro detectados</Text>
        </View>
        <Pressable
          accessibilityLabel="Cerrar foto ampliada"
          accessibilityRole="button"
          android_ripple={{ color: colors.rippleSalvia }}
          onPress={onClose}
          style={({ pressed }) => [styles.botonCerrarFoto, pressed ? styles.botonCerrarPresionado : undefined]}
        >
          <Text style={styles.botonCerrarTexto}>×</Text>
        </Pressable>
      </View>

      <View onLayout={actualizarTamanoFoto} style={styles.fotoAmpliada}>
        <Image source={{ uri: fotoUri }} resizeMode="contain" style={styles.fotoFondo} />
        {mascara != null && marcoFoto != null ? (
          <MascaraPintada mascara={mascara} rectangulo={marcoFoto} />
        ) : null}
        {cajaMascara != null ? <EsquinasFoco rectangulo={cajaMascara} /> : null}
        {esquinas != null ? <MarcadorArucoLeido esquinas={esquinas} /> : null}
        {posicionEtiqueta != null ? (
          <Text pointerEvents="none" style={[styles.etiquetaMarcador, posicionEtiqueta]}>
            Cuadro leído
          </Text>
        ) : null}
        {marcadoNoDisponible ? (
          <View pointerEvents="none" style={styles.avisoMarcado}>
            <Text style={styles.avisoMarcadoTexto}>No se pudo señalar la vaca ni el cuadro sobre la foto.</Text>
          </View>
        ) : null}
      </View>

      <View style={[styles.pieFotoAmpliada, { paddingBottom: insets.bottom + 14 }]}>
        <Text style={styles.pieFotoAmpliadaTexto}>
          Máscara verde: animal detectado. Cuadro amarillo: referencia leída.
        </Text>
      </View>
    </View>
  );
}

type ModoAjuste = 'contain' | 'cover';

function mapearBbox(
  bbox: [number, number, number, number],
  original: Tamano,
  mostrado: Tamano,
  modo: ModoAjuste,
): RectanguloMostrado {
  const [x0, y0, x1, y1] = bbox;
  return mapearRectangulo(
    {
      left: Math.min(x0, x1),
      top: Math.min(y0, y1),
      width: Math.abs(x1 - x0),
      height: Math.abs(y1 - y0),
    },
    original,
    mostrado,
    modo,
  );
}

function mapearEsquinasMarcador(
  esquinas: Point[],
  original: Tamano,
  mostrado: Tamano,
  modo: ModoAjuste,
): PuntoMostrado[] | null {
  if (esquinas.length !== 4) {
    return null;
  }

  return esquinas.map((esquina) => mapearPunto(esquina, original, mostrado, modo));
}

function rectanguloDesdePuntos(esquinas: PuntoMostrado[]): RectanguloMostrado {
  const xs = esquinas.map(({ x }) => x);
  const ys = esquinas.map(({ y }) => y);
  const left = Math.min(...xs);
  const top = Math.min(...ys);
  const right = Math.max(...xs);
  const bottom = Math.max(...ys);

  return { left, top, width: right - left, height: bottom - top };
}

function mapearPunto(
  punto: Point,
  original: Tamano,
  mostrado: Tamano,
  modo: ModoAjuste,
): PuntoMostrado {
  const { escala, offsetX, offsetY } = calcularAjuste(original, mostrado, modo);

  return {
    x: punto.x * escala + offsetX,
    y: punto.y * escala + offsetY,
  };
}

function mapearRectangulo(
  rectangulo: RectanguloMostrado,
  original: Tamano,
  mostrado: Tamano,
  modo: ModoAjuste,
): RectanguloMostrado {
  const { escala, offsetX, offsetY } = calcularAjuste(original, mostrado, modo);

  return {
    left: rectangulo.left * escala + offsetX,
    top: rectangulo.top * escala + offsetY,
    width: rectangulo.width * escala,
    height: rectangulo.height * escala,
  };
}

// R1 made the inline photo `cover`, so the overlay geometry has to follow the same
// scale the image uses; the fullscreen modal is still `contain`.
function calcularAjuste(original: Tamano, mostrado: Tamano, modo: ModoAjuste) {
  const escalaHorizontal = mostrado.width / original.width;
  const escalaVertical = mostrado.height / original.height;
  const escala =
    modo === 'cover'
      ? Math.max(escalaHorizontal, escalaVertical)
      : Math.min(escalaHorizontal, escalaVertical);
  const anchoRenderizado = original.width * escala;
  const altoRenderizado = original.height * escala;

  return {
    escala,
    offsetX: (mostrado.width - anchoRenderizado) / 2,
    offsetY: (mostrado.height - altoRenderizado) / 2,
  };
}

function calcularPosicionEtiquetaMarcador(
  rectangulo: RectanguloMostrado,
  cajaMascara: RectanguloMostrado | null,
  contenedor: Tamano,
): Pick<RectanguloMostrado, 'left' | 'top'> {
  // Kept in step with styles.etiquetaMarcador, which R1 grew to 14 px.
  const anchoEtiqueta = 118;
  const altoEtiqueta = 32;
  const margen = 8;
  const centrarVertical = rectangulo.top + (rectangulo.height - altoEtiqueta) / 2;
  const centrarHorizontal = rectangulo.left + (rectangulo.width - anchoEtiqueta) / 2;
  const candidatos = [
    { left: rectangulo.left + rectangulo.width + margen, top: centrarVertical },
    { left: rectangulo.left - anchoEtiqueta - margen, top: centrarVertical },
    { left: centrarHorizontal, top: rectangulo.top - altoEtiqueta - margen },
    { left: centrarHorizontal, top: rectangulo.top + rectangulo.height + margen },
  ].map((posicion) => ({
    left: Math.max(margen, Math.min(posicion.left, contenedor.width - anchoEtiqueta - margen)),
    top: Math.max(margen, Math.min(posicion.top, contenedor.height - altoEtiqueta - margen)),
  }));

  return candidatos.reduce((mejor, candidata) => {
    const solapamientoMejor = areaSolapamiento(mejor, cajaMascara, anchoEtiqueta, altoEtiqueta);
    const solapamientoCandidata = areaSolapamiento(candidata, cajaMascara, anchoEtiqueta, altoEtiqueta);
    return solapamientoCandidata < solapamientoMejor ? candidata : mejor;
  });
}

function areaSolapamiento(
  etiqueta: Pick<RectanguloMostrado, 'left' | 'top'>,
  cajaMascara: RectanguloMostrado | null,
  anchoEtiqueta: number,
  altoEtiqueta: number,
): number {
  if (cajaMascara == null) {
    return 0;
  }

  const izquierda = Math.max(etiqueta.left, cajaMascara.left);
  const superior = Math.max(etiqueta.top, cajaMascara.top);
  const derecha = Math.min(etiqueta.left + anchoEtiqueta, cajaMascara.left + cajaMascara.width);
  const inferior = Math.min(etiqueta.top + altoEtiqueta, cajaMascara.top + cajaMascara.height);
  return Math.max(0, derecha - izquierda) * Math.max(0, inferior - superior);
}

const styles = StyleSheet.create({
  resultadoPantalla: {
    flex: 1,
    backgroundColor: colors.crema,
  },
  resultadoScroll: {
    flex: 1,
  },
  resultadoContenido: {
    flexGrow: 1,
  },
  fotoResultado: {
    position: 'relative',
    height: 290,
    overflow: 'hidden',
    backgroundColor: colors.bosqueCamara,
  },
  fotoResultadoPresionada: {
    opacity: 0.94,
  },
  fotoFondo: {
    ...StyleSheet.absoluteFill,
  },
  chipCuadro: {
    position: 'absolute',
    right: 12,
    paddingVertical: 6,
    paddingHorizontal: 10,
    borderRadius: 8,
    backgroundColor: colors.maiz,
  },
  chipCuadroTexto: {
    color: colors.bosque,
    fontFamily: font.bold,
    fontSize: 14,
    lineHeight: 18,
  },
  mascaraPintada: {
    position: 'absolute',
    overflow: 'hidden',
  },
  tramoMascara: {
    position: 'absolute',
    backgroundColor: colors.mascara,
    opacity: 0.3,
  },
  foco: {
    position: 'absolute',
  },
  esquinaFoco: {
    position: 'absolute',
    width: 20,
    height: 20,
    borderColor: colors.focoVaca,
  },
  esquinaSuperiorIzquierda: {
    top: 0,
    left: 0,
    borderTopWidth: 3,
    borderLeftWidth: 3,
    borderTopLeftRadius: 8,
  },
  esquinaSuperiorDerecha: {
    top: 0,
    right: 0,
    borderTopWidth: 3,
    borderRightWidth: 3,
    borderTopRightRadius: 8,
  },
  esquinaInferiorIzquierda: {
    bottom: 0,
    left: 0,
    borderBottomWidth: 3,
    borderLeftWidth: 3,
    borderBottomLeftRadius: 8,
  },
  esquinaInferiorDerecha: {
    right: 0,
    bottom: 0,
    borderRightWidth: 3,
    borderBottomWidth: 3,
    borderBottomRightRadius: 8,
  },
  aristaMarcador: {
    position: 'absolute',
    height: GROSOR_ARISTA_MARCADOR,
    borderRadius: GROSOR_ARISTA_MARCADOR / 2,
    backgroundColor: colors.maiz,
    shadowColor: colors.bosqueCamara,
    shadowOpacity: 0.35,
    shadowRadius: 0,
    shadowOffset: { width: 0, height: 0 },
    elevation: 3,
  },
  esquinaMarcador: {
    position: 'absolute',
    width: 8,
    height: 8,
    borderWidth: 1,
    borderColor: colors.bosqueCamara,
    borderRadius: 4,
    backgroundColor: colors.maiz,
    elevation: 3,
  },
  etiquetaMarcador: {
    position: 'absolute',
    zIndex: 1,
    paddingVertical: 6,
    paddingHorizontal: 10,
    borderRadius: 8,
    color: colors.bosque,
    backgroundColor: colors.maiz,
    fontFamily: font.bold,
    fontSize: 14,
  },
  avisoMarcado: {
    position: 'absolute',
    right: 12,
    bottom: 12,
    left: 12,
    paddingVertical: 8,
    paddingHorizontal: 10,
    borderRadius: radius.chip,
    backgroundColor: colors.bosqueInstruccion,
  },
  avisoMarcadoTexto: {
    color: colors.crema,
    fontFamily: font.medium,
    fontSize: 15,
    lineHeight: 20,
    textAlign: 'center',
  },
  modalFotoPantalla: {
    flex: 1,
    backgroundColor: colors.bosqueCamara,
  },
  cabeceraFotoAmpliada: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingRight: 16,
    paddingBottom: 12,
    paddingLeft: 16,
  },
  tituloFotoAmpliada: {
    flex: 1,
    minWidth: 0,
  },
  tituloFotoAmpliadaTexto: {
    color: colors.crema,
    fontFamily: font.bold,
    fontSize: 18,
    lineHeight: 23,
  },
  subtituloFotoAmpliada: {
    marginTop: 1,
    color: colors.textoClaroSec,
    fontFamily: font.regular,
    fontSize: 15,
    lineHeight: 20,
  },
  botonCerrarFoto: {
    width: 56,
    height: 56,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: colors.salvia,
    borderRadius: 28,
  },
  botonCerrarPresionado: {
    opacity: 0.8,
  },
  botonCerrarTexto: {
    marginTop: -3,
    color: colors.crema,
    fontFamily: font.regular,
    fontSize: 34,
    lineHeight: 38,
  },
  fotoAmpliada: {
    flex: 1,
    position: 'relative',
    overflow: 'hidden',
    marginHorizontal: 12,
    marginBottom: 12,
    backgroundColor: colors.bosqueProfundo,
  },
  pieFotoAmpliada: {
    paddingTop: 10,
    paddingHorizontal: 16,
    borderTopWidth: 1,
    borderTopColor: colors.bordeClaro,
    backgroundColor: colors.bosqueProfundo,
  },
  pieFotoAmpliadaTexto: {
    color: colors.textoClaroSec,
    fontFamily: font.regular,
    fontSize: 15,
    lineHeight: 20,
    textAlign: 'center',
  },
  barraResumenCompacta: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 10,
    paddingHorizontal: 16,
    backgroundColor: colors.bosque,
    borderBottomWidth: 1,
    borderBottomColor: colors.bordeClaro,
    zIndex: 10,
  },
  resumenCompactoInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  resumenCompactoPeso: {
    color: colors.crema,
    fontFamily: font.black,
    fontSize: 22,
    lineHeight: 26,
  },
  resumenCompactoMargen: {
    color: colors.textoClaroSec,
    fontFamily: font.medium,
    fontSize: 15,
    lineHeight: 20,
  },
  resumenCompactoPunto: {
    color: colors.salviaClara,
    fontFamily: font.bold,
    fontSize: 20,
    lineHeight: 22,
  },
  botonOcultarTeclado: {
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: radius.chip,
    borderWidth: 1,
    borderColor: colors.salviaClara,
    backgroundColor: 'rgba(182, 214, 185, 0.12)',
  },
  botonOcultarPresionado: {
    opacity: 0.7,
  },
  textoOcultarTeclado: {
    color: colors.salviaClara,
    fontFamily: font.bold,
    fontSize: 15,
  },
  panelResultado: {
    paddingTop: 12,
    paddingHorizontal: 16,
    backgroundColor: colors.crema,
  },
  resumenPeso: {
    flexShrink: 0,
  },
  overline: {
    ...type.overline,
    color: colors.tierra,
    fontSize: 14,
  },
  filaPeso: {
    flexDirection: 'row',
    alignItems: 'baseline',
    flexWrap: 'wrap',
    gap: 8,
    marginTop: 0,
  },
  peso: {
    ...type.pesoGigante,
    color: colors.verdeTinta,
    fontSize: 96,
    letterSpacing: -5,
    lineHeight: 96,
  },
  unidad: {
    color: colors.verdeTinta,
    fontFamily: font.bold,
    fontSize: 32,
    lineHeight: 36,
  },
  margenMetodo: {
    marginTop: 4,
    marginBottom: 4,
    color: colors.textoNeutro,
    fontFamily: font.regular,
    fontSize: 15,
    lineHeight: 20,
  },
  formulario: {
    gap: 10,
    paddingTop: 10,
  },
  etiquetaCampo: {
    color: colors.tierra,
    fontFamily: font.bold,
    fontSize: 13,
    letterSpacing: 1,
    textTransform: 'uppercase',
  },
  campoContenedor: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    height: 56,
    paddingHorizontal: 14,
    borderWidth: 2,
    borderColor: colors.bordeTarjeta,
    borderRadius: radius.input,
    backgroundColor: colors.tarjeta,
  },
  campo: {
    flex: 1,
    minWidth: 0,
    height: '100%',
    paddingVertical: 0,
    color: colors.verdeTinta,
    fontFamily: font.regular,
    fontSize: 18,
  },
  reglaCampo: {
    color: colors.grisCalido,
    fontFamily: font.bold,
    fontSize: 13,
  },
  campoError: {
    borderColor: colors.error,
  },
  campoEnfocado: {
    borderColor: colors.maiz,
    borderWidth: 2,
    shadowColor: colors.maiz,
    shadowOpacity: 0.45,
    shadowRadius: 5,
    shadowOffset: { width: 0, height: 0 },
    elevation: 3,
  },
  sugerenciasBloque: {
    gap: 8,
  },
  sugerenciasEtiqueta: {
    color: colors.tierra,
    fontFamily: font.bold,
    fontSize: 15,
    lineHeight: 20,
  },
  sugerenciasFila: {
    flexDirection: 'row',
    gap: 8,
    paddingRight: 4,
  },
  chipArete: {
    height: 40,
    justifyContent: 'center',
    paddingHorizontal: 14,
    borderRadius: 12,
    backgroundColor: colors.maiz,
  },
  chipAretePresionado: {
    opacity: 0.8,
  },
  textoChipArete: {
    color: colors.bosque,
    fontFamily: font.black,
    fontSize: 16,
  },
  ayudaGuardar: {
    color: colors.tierra,
    fontFamily: font.medium,
    fontSize: 15,
    lineHeight: 20,
    textAlign: 'center',
  },
  errorGuardar: {
    color: colors.error,
    fontFamily: font.medium,
    fontSize: 15,
    lineHeight: 20,
  },
  accionesResultado: {
    gap: 10,
    marginTop: 18,
  },
  rechazoPantalla: {
    flex: 1,
    backgroundColor: colors.bosqueCamara,
  },
  overlayRechazo: {
    ...StyleSheet.absoluteFill,
    backgroundColor: colors.overlayRechazo,
  },
  rechazoOverline: {
    position: 'absolute',
    left: 22,
    color: colors.maiz,
    fontFamily: font.bold,
    fontSize: 13,
    letterSpacing: 1.7,
    textTransform: 'uppercase',
    textShadowColor: colors.bosqueCamara,
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 4,
  },
  zonaRechazo: {
    position: 'absolute',
    alignItems: 'flex-start',
  },
  zonaRecuadro: {
    width: LADO_ZONA_RECHAZO,
    height: LADO_ZONA_RECHAZO,
    borderWidth: 3,
    borderStyle: 'dashed',
    borderColor: colors.maiz,
    borderRadius: 10,
  },
  zonaEtiqueta: {
    marginTop: 8,
    paddingVertical: 6,
    paddingHorizontal: 10,
    borderRadius: 8,
    color: colors.bosque,
    backgroundColor: colors.maiz,
    fontFamily: font.bold,
    fontSize: 14,
    lineHeight: 18,
  },
  rechazoPanel: {
    position: 'absolute',
    right: 0,
    bottom: 0,
    left: 0,
    gap: 14,
    paddingTop: 20,
    paddingHorizontal: 20,
    borderTopLeftRadius: radius.tarjeta,
    borderTopRightRadius: radius.tarjeta,
    backgroundColor: colors.bosqueProfundo,
  },
  rechazoFila: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
  },
  rechazoIcono: {
    width: 44,
    height: 44,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 22,
    backgroundColor: colors.maiz,
  },
  rechazoSigno: {
    color: colors.bosque,
    fontFamily: font.black,
    fontSize: 28,
    lineHeight: 32,
  },
  rechazoTitulo: {
    flex: 1,
    color: colors.crema,
    fontFamily: font.black,
    fontSize: 28,
    letterSpacing: -0.8,
    lineHeight: 32,
  },
  rechazoConsejo: {
    color: colors.crema,
    fontFamily: font.regular,
    fontSize: 19,
    lineHeight: 27,
  },
  rechazoAcciones: {
    gap: 10,
    marginTop: 4,
  },
});
