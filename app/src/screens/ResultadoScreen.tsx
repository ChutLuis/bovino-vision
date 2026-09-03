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
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { guardarAnimal, guardarEstimacion } from '../data/db/dao';
import { eliminarFotoPrivada, guardarFotoPrivada } from '../data/photos';
import type { CausaRechazo, EstimacionExitosa } from '../domain/types';
import type { ResultadoScreenProps } from '../navigation/types';
import type { MascaraVisual, Point } from '../vision/types';
import { BotonPrimario, BotonSecundario } from '../ui/Botones';
import { colors, font, radius, type } from '../ui/theme';

const MENSAJES_RECHAZO: Record<CausaRechazo, string> = {
  sin_vaca: 'No se ve la vaca completa. Aléjese un poco y tome la foto de lado.',
  sin_marcador: 'No se ve el cuadro de referencia. Revise que esté visible y limpio.',
  marcador_ilegible:
    'El cuadro de referencia se ve borroso o de lado. Póngalo derecho, junto al costado de la vaca.',
};

const TITULOS_RECHAZO: Record<CausaRechazo, string> = {
  sin_vaca: 'No se ve la vaca completa',
  sin_marcador: 'No se ve el cuadro',
  marcador_ilegible: 'El cuadro no se puede leer',
};

const CONSEJOS_RECHAZO: Record<CausaRechazo, string> = {
  sin_vaca:
    'Camine unos pasos hacia atrás. La vaca debe caber entera en la pantalla, de la cabeza a la cola.',
  sin_marcador:
    'Ponga el cuadro junto al costado de la vaca, sin lodo ni sombra encima, y tome la foto otra vez.',
  marcador_ilegible:
    'Enderece el cuadro para que mire hacia la cámara y sostenga el teléfono firme al disparar.',
};

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

export function ResultadoScreen({ navigation, route }: ResultadoScreenProps) {
  const { resultado } = route.params;
  const insets = useSafeAreaInsets();

  if (!resultado.ok) {
    return (
      <View style={styles.rechazoPantalla}>
        <StatusBar style="light" />
        <Image source={{ uri: resultado.foto_uri }} resizeMode="cover" style={styles.fotoFondo} />
        <View pointerEvents="none" style={styles.overlayRechazo} />
        <View
          style={[
            styles.rechazoContenido,
            { paddingTop: insets.top + 32, paddingBottom: insets.bottom + 16 },
          ]}
        >
          <View style={styles.rechazoCentro}>
            <View style={styles.rechazoIcono}>
              <Text style={styles.rechazoSigno}>!</Text>
            </View>
            <Text style={styles.rechazoTitulo}>{TITULOS_RECHAZO[resultado.causa]}</Text>
            <Text style={styles.rechazoMensaje}>{MENSAJES_RECHAZO[resultado.causa]}</Text>
            <View style={styles.consejoTarjeta}>
              <Text style={styles.consejoOverline}>Cómo corregirlo</Text>
              <Text style={styles.consejoTexto}>{CONSEJOS_RECHAZO[resultado.causa]}</Text>
            </View>
          </View>
          <BotonPrimario titulo="Volver a tomar" onPress={() => navigation.popToTop()} />
        </View>
      </View>
    );
  }

  return (
    <ResultadoExitoso
      resultado={resultado}
      onRepetir={() => navigation.popToTop()}
      onGuardar={() => navigation.replace('Historial')}
      insetInferior={insets.bottom}
    />
  );
}

interface ResultadoExitosoProps {
  resultado: EstimacionExitosa;
  onRepetir: () => void;
  onGuardar: () => void;
  insetInferior: number;
}

function ResultadoExitoso({
  resultado,
  onRepetir,
  onGuardar,
  insetInferior,
}: ResultadoExitosoProps) {
  const insets = useSafeAreaInsets();
  const [arete, setArete] = useState('');
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
      onGuardar();
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
      ? mapearBbox(resultado.mascara.bbox_original_px, tamanoOriginal, tamanoFoto)
      : null;
  const marcoFoto =
    tamanoFoto != null && tamanoOriginal != null
      ? mapearRectangulo(
          { left: 0, top: 0, width: tamanoOriginal.width, height: tamanoOriginal.height },
          tamanoOriginal,
          tamanoFoto,
        )
      : null;
  const esquinasMarcador =
    tamanoFoto != null && tamanoOriginal != null
      ? mapearEsquinasMarcador(resultado.esquinas_marcador, tamanoOriginal, tamanoFoto)
      : null;
  const cajaMarcador =
    esquinasMarcador != null ? rectanguloDesdePuntos(esquinasMarcador) : null;
  const posicionEtiquetaMarcador =
    cajaMarcador != null && tamanoFoto != null
      ? calcularPosicionEtiquetaMarcador(cajaMarcador, cajaMascara, tamanoFoto)
      : null;
  const infoConfianza = calcularInfoConfianza(resultado.intervalo_modelo, resultado.peso_kg);

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
        <View style={[styles.barraResumenCompacta, { paddingTop: Math.max(12, insets.top + 8) }]}>
          <View style={styles.resumenCompactoInfo}>
            <Text style={styles.resumenCompactoPeso}>
              {`${Math.round(resultado.peso_kg)} kg`}
            </Text>
            <Text style={styles.resumenCompactoPunto}>·</Text>
            <View style={[styles.chipCompacto, { backgroundColor: infoConfianza.colorBg }]}>
              <View style={[styles.puntoIntervalo, { backgroundColor: infoConfianza.colorPunto }]} />
              <Text style={[styles.textoChipCompacto, { color: infoConfianza.colorTexto }]}>
                {`± ${infoConfianza.margenKg} kg`}
              </Text>
            </View>
          </View>
          <Pressable
            accessibilityLabel="Ocultar teclado para ver foto completa"
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
            <Text style={styles.textoOcultarTeclado}>Ver foto</Text>
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
          accessibilityHint="Abre una vista de pantalla completa con la segmentación y el marcador."
          accessibilityLabel="Ampliar foto con segmentación"
          accessibilityRole="button"
          android_ripple={{ color: colors.rippleSalvia }}
          onLayout={actualizarTamanoFoto}
          onPress={abrirFotoAmpliada}
          style={({ pressed }) => [
            styles.fotoResultado,
            pressed ? styles.fotoResultadoPresionada : undefined,
          ]}
        >
          <Image source={{ uri: resultado.foto_uri }} resizeMode="contain" style={styles.fotoFondo} />
          {resultado.overlay_mascara != null && marcoFoto != null ? (
            <MascaraPintada mascara={resultado.overlay_mascara} rectangulo={marcoFoto} />
          ) : null}
          {cajaMascara != null ? <EsquinasFoco rectangulo={cajaMascara} /> : null}
          {esquinasMarcador != null ? (
            <>
              <MarcadorArucoLeido esquinas={esquinasMarcador} />
              {posicionEtiquetaMarcador != null ? (
                <Text pointerEvents="none" style={[styles.etiquetaMarcador, posicionEtiquetaMarcador]}>
                  Cuadro leído
                </Text>
              ) : null}
            </>
          ) : null}
          {marcadoNoDisponible ? (
            <View pointerEvents="none" style={styles.avisoMarcado}>
              <Text style={styles.avisoMarcadoTexto}>No se pudo mostrar el marcado sobre la foto.</Text>
            </View>
          ) : null}
          <View pointerEvents="none" style={styles.ayudaAmpliar}>
            <Text style={styles.ayudaAmpliarTexto}>Toca para ampliar</Text>
          </View>
        </Pressable>

        <View style={styles.panelResultado}>
          <View style={styles.resumenPeso}>
            <Text style={styles.overline}>Peso estimado</Text>
            <View style={styles.filaPeso}>
              <Text style={styles.peso}>{Math.round(resultado.peso_kg)}</Text>
              <Text style={styles.unidad}>kg</Text>
              <View style={[styles.chipIntervalo, { backgroundColor: infoConfianza.colorBg }]}>
                <View style={[styles.puntoIntervalo, { backgroundColor: infoConfianza.colorPunto }]} />
                <Text style={[styles.textoIntervalo, { color: infoConfianza.colorTexto }]}>
                  {infoConfianza.etiqueta}
                </Text>
              </View>
            </View>
            <Text style={[styles.notaConfianza, { color: infoConfianza.colorTexto }]}>
              {infoConfianza.nota}
            </Text>
            <View style={styles.pruebaFoto}>
              <View style={styles.puntoPrueba} />
              <Text style={styles.pruebaDetalle}>Vaca y cuadro ubicados en la foto.</Text>
            </View>
          </View>

          <View style={styles.formulario}>
            <Text style={styles.etiquetaCampo}>Arete obligatorio</Text>
            <TextInput
              accessibilityLabel="Número de arete obligatorio"
              autoCapitalize="characters"
              inputMode="numeric"
              keyboardType="numeric"
              maxLength={6}
              onChangeText={actualizarArete}
              onBlur={() => actualizarFocoArete(false)}
              onFocus={() => actualizarFocoArete(true)}
              onPressIn={scrollAlFinal}
              onSubmitEditing={() => void guardar()}
              placeholder="Arete (ej. 8492)"
              placeholderTextColor={colors.grisCalido}
              ref={areteRef}
              returnKeyType="done"
              style={[
                styles.campo,
                areteEnfocado ? styles.campoEnfocado : undefined,
                error === 'Ingrese el arete antes de guardar.' ? styles.campoError : undefined,
              ]}
              value={arete}
            />
            <Text style={styles.notaTeclado}>Solo números — máx. 6 dígitos</Text>
            {error != null ? <Text style={styles.errorGuardar}>{error}</Text> : null}
          </View>

          <View style={styles.accionesResultado}>
            <BotonPrimario
              accessibilityLabel="Guardar en historial"
              alto={56}
              disabled={guardando}
              titulo={guardando ? 'Guardando...' : 'Guardar pesaje'}
              onPress={() => void guardar()}
            />
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
      ? mapearBbox(mascaraBbox, tamanoOriginal, tamanoFoto)
      : null;
  const marcoFoto =
    tamanoFoto != null && tamanoOriginal != null
      ? mapearRectangulo(
          { left: 0, top: 0, width: tamanoOriginal.width, height: tamanoOriginal.height },
          tamanoOriginal,
          tamanoFoto,
        )
      : null;
  const esquinas =
    tamanoFoto != null && tamanoOriginal != null
      ? mapearEsquinasMarcador(esquinasMarcador, tamanoOriginal, tamanoFoto)
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
            <Text style={styles.avisoMarcadoTexto}>No se pudo mostrar el marcado sobre la foto.</Text>
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

function mapearBbox(
  bbox: [number, number, number, number],
  original: Tamano,
  mostrado: Tamano,
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
  );
}

function mapearEsquinasMarcador(
  esquinas: Point[],
  original: Tamano,
  mostrado: Tamano,
): PuntoMostrado[] | null {
  if (esquinas.length !== 4) {
    return null;
  }

  return esquinas.map((esquina) => mapearPunto(esquina, original, mostrado));
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

function mapearPunto(punto: Point, original: Tamano, mostrado: Tamano): PuntoMostrado {
  const { escala, offsetX, offsetY } = calcularAjusteAspectFit(original, mostrado);

  return {
    x: punto.x * escala + offsetX,
    y: punto.y * escala + offsetY,
  };
}

function mapearRectangulo(
  rectangulo: RectanguloMostrado,
  original: Tamano,
  mostrado: Tamano,
): RectanguloMostrado {
  const { escala, offsetX, offsetY } = calcularAjusteAspectFit(original, mostrado);

  return {
    left: rectangulo.left * escala + offsetX,
    top: rectangulo.top * escala + offsetY,
    width: rectangulo.width * escala,
    height: rectangulo.height * escala,
  };
}

function calcularAjusteAspectFit(original: Tamano, mostrado: Tamano) {
  const escalaHorizontal = mostrado.width / original.width;
  const escalaVertical = mostrado.height / original.height;
  const escala = Math.min(escalaHorizontal, escalaVertical);
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
  const anchoEtiqueta = 102;
  const altoEtiqueta = 26;
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

interface InfoConfianza {
  margenKg: number;
  etiqueta: string;
  nota: string;
  colorBg: string;
  colorTexto: string;
  colorPunto: string;
}

function calcularInfoConfianza(intervalo: unknown, pesoKg: number): InfoConfianza {
  const valor =
    typeof intervalo === 'number' && Number.isFinite(intervalo) && intervalo > 0
      ? intervalo
      : Math.round(pesoKg * 0.035);
  const margenKg = Math.max(1, Math.round(valor));

  if (margenKg < 10) {
    return {
      margenKg,
      etiqueta: `± ${margenKg} kg`,
      nota: `Lectura válida · margen estimado ±${margenKg} kg`,
      colorBg: '#dcefdb',
      colorTexto: '#1c7a37',
      colorPunto: '#2b7a3e',
    };
  }
  if (margenKg <= 25) {
    return {
      margenKg,
      etiqueta: `± ${margenKg} kg`,
      nota: `Lectura válida · margen estimado ±${margenKg} kg`,
      colorBg: '#f6ebc2',
      colorTexto: '#8a6a00',
      colorPunto: '#cf9a12',
    };
  }
  return {
    margenKg,
    etiqueta: `± ${margenKg} kg`,
    nota: 'Margen amplio — recomendable volver a tomar la foto.',
    colorBg: '#f3d9c2',
    colorTexto: '#9a4712',
    colorPunto: '#c8612a',
  };
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
    height: 212,
    overflow: 'hidden',
    backgroundColor: colors.bosqueCamara,
  },
  fotoResultadoPresionada: {
    opacity: 0.94,
  },
  fotoFondo: {
    ...StyleSheet.absoluteFill,
  },
  ayudaAmpliar: {
    position: 'absolute',
    right: 8,
    bottom: 8,
    paddingVertical: 5,
    paddingHorizontal: 8,
    borderRadius: radius.chip,
    backgroundColor: colors.bosqueEtiqueta,
  },
  ayudaAmpliarTexto: {
    color: colors.crema,
    fontFamily: font.bold,
    fontSize: 11,
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
    paddingVertical: 3,
    paddingHorizontal: 8,
    borderRadius: 6,
    color: colors.bosque,
    backgroundColor: colors.maiz,
    fontFamily: font.bold,
    fontSize: 11,
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
    fontSize: 14,
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
    color: colors.salviaClara,
    fontFamily: font.regular,
    fontSize: 13,
    lineHeight: 18,
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
    fontSize: 13,
    lineHeight: 18,
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
  resumenCompactoPunto: {
    color: colors.salviaClara,
    fontFamily: font.bold,
    fontSize: 20,
    lineHeight: 22,
  },
  chipCompacto: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    paddingVertical: 3,
    paddingHorizontal: 8,
    borderRadius: radius.chip,
  },
  textoChipCompacto: {
    fontFamily: font.bold,
    fontSize: 14,
    lineHeight: 16,
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
    fontSize: 13,
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
    fontSize: 60,
    lineHeight: 64,
  },
  unidad: {
    color: colors.verdeTinta,
    fontFamily: font.bold,
    fontSize: 26,
    lineHeight: 32,
  },
  chipIntervalo: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    alignSelf: 'center',
    paddingVertical: 4,
    paddingHorizontal: 10,
    borderRadius: radius.chip,
    backgroundColor: colors.chipClaro,
  },
  puntoIntervalo: {
    width: 7,
    height: 7,
    borderRadius: 4,
  },
  textoIntervalo: {
    fontFamily: font.bold,
    fontSize: 15,
    lineHeight: 18,
  },
  notaConfianza: {
    marginTop: 4,
    marginBottom: 4,
    fontFamily: font.medium,
    fontSize: 13,
    lineHeight: 18,
  },
  pruebaFoto: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 9,
    marginTop: 6,
    paddingVertical: 6,
    borderTopWidth: 1,
    borderBottomWidth: 1,
    borderColor: colors.bordeTarjeta,
  },
  puntoPrueba: {
    width: 7,
    height: 7,
    borderRadius: 4,
    backgroundColor: colors.mascara,
  },
  pruebaDetalle: {
    flex: 1,
    color: colors.verdeTinta,
    fontFamily: font.regular,
    fontSize: 13,
    lineHeight: 18,
  },
  formulario: {
    gap: 10,
    paddingTop: 10,
  },
  etiquetaCampo: {
    color: colors.tierra,
    fontFamily: font.bold,
    fontSize: 11,
    letterSpacing: 1,
    textTransform: 'uppercase',
  },
  campo: {
    height: 56,
    flex: 1,
    minWidth: 0,
    paddingHorizontal: 14,
    borderWidth: 2,
    borderColor: colors.bordeTarjeta,
    borderRadius: radius.input,
    color: colors.verdeTinta,
    backgroundColor: colors.tarjeta,
    fontFamily: font.regular,
    fontSize: 18,
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
  notaTeclado: {
    color: colors.grisCalido,
    fontFamily: font.regular,
    fontSize: 12,
    lineHeight: 16,
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
  rechazoContenido: {
    flex: 1,
    paddingHorizontal: 28,
  },
  rechazoCentro: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  rechazoIcono: {
    width: 92,
    height: 92,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 28,
    borderRadius: 46,
    backgroundColor: colors.maiz,
  },
  rechazoSigno: {
    color: colors.bosque,
    fontFamily: font.black,
    fontSize: 54,
    lineHeight: 60,
  },
  rechazoTitulo: {
    color: colors.crema,
    fontFamily: font.black,
    fontSize: 32,
    lineHeight: 38,
    textAlign: 'center',
  },
  rechazoMensaje: {
    marginTop: 18,
    color: colors.textoRechazo,
    fontFamily: font.regular,
    fontSize: 22,
    lineHeight: 32,
    textAlign: 'center',
  },
  consejoTarjeta: {
    width: '100%',
    marginTop: 32,
    paddingVertical: 18,
    paddingHorizontal: 20,
    borderWidth: 2,
    borderColor: colors.cremaTarjetaBorde,
    borderRadius: 18,
    backgroundColor: colors.cremaTarjetaFondo,
  },
  consejoOverline: {
    marginBottom: 8,
    color: colors.maiz,
    fontFamily: font.bold,
    fontSize: 15,
    letterSpacing: 1.5,
    textTransform: 'uppercase',
  },
  consejoTexto: {
    color: colors.crema,
    fontFamily: font.regular,
    fontSize: 20,
    lineHeight: 29,
  },
});
