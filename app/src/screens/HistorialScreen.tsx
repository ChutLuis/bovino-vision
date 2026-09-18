import {
  Alert,
  BackHandler,
  FlatList,
  Image,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { useCallback, useEffect, useState } from 'react';
import { StatusBar } from 'expo-status-bar';
import Swipeable from 'react-native-gesture-handler/Swipeable';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import {
  borrarEstimacion,
  listarAnimales,
  listarEstimaciones,
  listarFilasExportacion,
  type AnimalConResumen,
  type Estimacion,
} from '../data/db/dao';
import { exportarCsv } from '../data/export/csv';
import { eliminarFotoPrivada } from '../data/photos';
import type { HistorialScreenProps, PesadaGuardada } from '../navigation/types';
import { BotonPrimario, BotonSecundario } from '../ui/Botones';
import { colors, font, radius } from '../ui/theme';

export function HistorialScreen({ navigation, route }: HistorialScreenProps) {
  const insets = useSafeAreaInsets();
  const guardado = route.params?.guardado;
  const [confirmacion, setConfirmacion] = useState<PesadaGuardada | null>(guardado ?? null);
  const [animales, setAnimales] = useState<AnimalConResumen[]>([]);
  const [seleccionado, setSeleccionado] = useState<AnimalConResumen | null>(null);
  const [estimaciones, setEstimaciones] = useState<Estimacion[]>([]);
  const [cargando, setCargando] = useState(true);
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [mensajeDetalle, setMensajeDetalle] = useState<string | null>(null);
  const [busqueda, setBusqueda] = useState('');

  const cargarAnimales = useCallback(async (): Promise<void> => {
    setCargando(true);
    setMensaje(null);

    try {
      setAnimales(await listarAnimales());
    } catch (cause) {
      console.error('No se pudo cargar el historial.', cause);
      setMensaje('No se pudo abrir el historial. Inténtelo otra vez.');
    } finally {
      setCargando(false);
    }
  }, []);

  useEffect(() => {
    void cargarAnimales();
  }, [cargarAnimales]);

  // The band answers "did it save?" for three seconds and then gets out of the way.
  useEffect(() => {
    if (guardado == null) {
      return;
    }

    setConfirmacion(guardado);
    const temporizador = setTimeout(() => setConfirmacion(null), 3000);

    return () => clearTimeout(temporizador);
  }, [guardado]);

  const seleccionarAnimal = async (animal: AnimalConResumen): Promise<void> => {
    setSeleccionado(animal);
    setMensajeDetalle(null);

    try {
      setEstimaciones(await listarEstimaciones(animal.id));
    } catch (cause) {
      console.error('No se pudieron cargar las pesadas del animal.', cause);
      setMensajeDetalle('No se pudieron abrir las pesadas de este animal.');
    }
  };

  const exportar = async (): Promise<void> => {
    setMensaje(null);

    try {
      await exportarCsv(await listarFilasExportacion());
      setMensaje('Historial listo para compartir.');
    } catch (cause) {
      console.error('No se pudo compartir el historial.', cause);
      setMensaje('No se pudo compartir el historial. Inténtelo otra vez.');
    }
  };

  const terminoBusqueda = busqueda.trim().toLowerCase();
  const animalesFiltrados = animales.filter((animal) => {
    if (terminoBusqueda.length === 0) {
      return true;
    }
    const matchArete = animal.arete.toLowerCase().includes(terminoBusqueda);
    const matchNombre = animal.nombre?.toLowerCase().includes(terminoBusqueda) ?? false;
    return matchArete || matchNombre;
  });

  const totalPesadas = animales.reduce((total, animal) => total + animal.estimaciones_count, 0);
  const resumen = `${animales.length} ${animales.length === 1 ? 'animal' : 'animales'} · ${totalPesadas} ${totalPesadas === 1 ? 'pesada' : 'pesadas'}`;
  const enDetalle = seleccionado != null;
  const titulo = enDetalle ? `Arete ${seleccionado.arete}` : 'Historial';
  const conteoPesadas = `${estimaciones.length} ${estimaciones.length === 1 ? 'pesada' : 'pesadas'}`;
  const subtitulo = enDetalle
    ? conteoPesadas
    : terminoBusqueda.length > 0
      ? `${animalesFiltrados.length} ${animalesFiltrados.length === 1 ? 'resultado' : 'resultados'}`
      : resumen;
  const tendencia = tendenciaDesde(estimaciones);

  const volver = (): void => {
    if (enDetalle) {
      setSeleccionado(null);
      return;
    }

    navigation.popToTop();
  };

  // One "back" only: inside the detail it returns to the list, not out of the history.
  useEffect(() => {
    if (seleccionado == null) {
      return;
    }

    const suscripcion = BackHandler.addEventListener('hardwareBackPress', () => {
      setSeleccionado(null);
      return true;
    });

    return () => suscripcion.remove();
  }, [seleccionado]);

  // The row is gone; if it was the animal's last one, the animal went with it.
  const borrarPesada = async (estimacion: Estimacion): Promise<void> => {
    setMensajeDetalle(null);

    try {
      const resultado = await borrarEstimacion(estimacion.id);

      if (resultado.ruta_foto != null) {
        try {
          eliminarFotoPrivada(resultado.ruta_foto);
        } catch (cause) {
          // The row is what matters; a leftover file is not worth failing the delete over.
          console.error('No se pudo borrar la foto de la pesada.', cause);
        }
      }

      await cargarAnimales();

      if (resultado.animal_borrado) {
        setSeleccionado(null);
        setEstimaciones([]);
        return;
      }

      setEstimaciones(await listarEstimaciones(estimacion.animal_id));
    } catch (cause) {
      console.error('No se pudo borrar la pesada.', cause);
      setMensajeDetalle('No se pudo borrar esta pesada. Inténtelo otra vez.');
    }
  };

  const confirmarBorrado = (estimacion: Estimacion): void => {
    Alert.alert(
      'Borrar la pesada',
      `¿Borrar la pesada de las ${horaLegible(estimacion.timestamp)}? No se puede deshacer.`,
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Borrar',
          style: 'destructive',
          onPress: () => void borrarPesada(estimacion),
        },
      ],
    );
  };

  return (
    <View style={styles.pantalla}>
      <StatusBar style="light" />
      <View style={[styles.encabezado, { paddingTop: insets.top + 18 }]}>
        <Pressable
          accessibilityLabel={enDetalle ? 'Volver al historial' : 'Volver a la captura'}
          accessibilityRole="button"
          android_ripple={{ color: colors.rippleSalvia }}
          onPress={volver}
          style={({ pressed }) => [styles.botonVolver, pressed ? styles.volverPresionado : undefined]}
        >
          <Text style={styles.chevron}>{'\u2039'}</Text>
        </Pressable>
        <View style={styles.titulosEncabezado}>
          <Text numberOfLines={1} style={styles.tituloEncabezado}>
            {titulo}
          </Text>
          <Text numberOfLines={1} style={styles.subtituloEncabezado}>
            {enDetalle && tendencia != null ? (
              <>
                {`${conteoPesadas} · `}
                <Text style={styles.tendencia}>{tendencia}</Text>
              </>
            ) : (
              subtitulo
            )}
          </Text>
        </View>
      </View>

      {!enDetalle ? (
        <View style={styles.busquedaContenedor}>
          <Text style={styles.lupaIcono}>⌕</Text>
          <TextInput
            accessibilityLabel="Buscar por número de arete"
            autoCapitalize="none"
            autoCorrect={false}
            inputMode="numeric"
            onChangeText={setBusqueda}
            placeholder="Buscar arete…"
            placeholderTextColor={colors.grisCalido}
            style={styles.campoBusqueda}
            value={busqueda}
          />
          {busqueda.length > 0 ? (
            <Pressable
              accessibilityLabel="Limpiar búsqueda"
              accessibilityRole="button"
              android_ripple={{ color: colors.rippleSecundario }}
              onPress={() => setBusqueda('')}
              style={({ pressed }) => [
                styles.botonLimpiarBusqueda,
                pressed ? styles.botonLimpiarPresionado : undefined,
              ]}
            >
              <Text style={styles.textoLimpiarBusqueda}>✕</Text>
            </Pressable>
          ) : null}
        </View>
      ) : null}

      {!enDetalle && confirmacion != null ? (
        <View style={styles.banda}>
          <View style={styles.bandaIcono}>
            <Text style={styles.bandaCheck}>{'\u2713'}</Text>
          </View>
          <Text style={styles.bandaTexto}>
            {`Pesada guardada · Arete ${confirmacion.arete} · ${confirmacion.pesoKg} kg`}
          </Text>
        </View>
      ) : null}

      {enDetalle ? (
        <FlatList<Estimacion>
          contentContainerStyle={styles.contenidoLista}
          data={estimaciones}
          keyExtractor={(estimacion) => String(estimacion.id)}
          ListEmptyComponent={
            <EstadoVacio texto={mensajeDetalle ?? 'Este animal todavía no tiene pesadas.'} />
          }
          ListFooterComponent={
            estimaciones.length > 0 ? (
              <Text style={styles.ayudaBorrado}>
                Deslice una pesada a la izquierda para borrarla
              </Text>
            ) : null
          }
          renderItem={({ index, item }) => (
            <FilaPesada
              anterior={estimaciones[index + 1] ?? null}
              estimacion={item}
              onBorrar={() => confirmarBorrado(item)}
            />
          )}
          showsVerticalScrollIndicator={false}
        />
      ) : (
        <FlatList<AnimalConResumen>
          contentContainerStyle={styles.contenidoLista}
          data={animalesFiltrados}
          keyExtractor={(animal) => String(animal.id)}
          keyboardDismissMode="on-drag"
          keyboardShouldPersistTaps="handled"
          ListEmptyComponent={
            terminoBusqueda.length > 0 ? (
              <EstadoVacio
                esBusqueda={true}
                onLimpiarBusqueda={() => setBusqueda('')}
                texto="Ningún arete coincide con la búsqueda."
              />
            ) : (
              <EstadoVacio
                mostrarRegistro={!cargando && mensaje == null}
                texto={mensaje ?? (cargando ? 'Cargando historial…' : 'Todavía no hay animales guardados.')}
              />
            )
          }
          ListHeaderComponent={mensaje != null && animales.length > 0 ? <Mensaje texto={mensaje} /> : null}
          refreshControl={
            <RefreshControl
              colors={[colors.verdeMedio]}
              onRefresh={() => void cargarAnimales()}
              refreshing={cargando}
              tintColor={colors.verdeMedio}
            />
          }
          renderItem={({ item }) => (
            <TarjetaAnimal
              animal={item}
              destacada={confirmacion?.arete === item.arete}
              onPress={() => void seleccionarAnimal(item)}
            />
          )}
          showsVerticalScrollIndicator={false}
        />
      )}

      <View style={[styles.pie, { paddingBottom: insets.bottom + 16 }]}>
        <BotonPrimario
          alto={70}
          titulo={enDetalle ? 'Pesar este animal' : 'Pesar otro animal'}
          onPress={() => {
            if (seleccionado != null) {
              navigation.navigate('Captura', { aretePrellenado: seleccionado.arete });
              return;
            }

            navigation.popToTop();
          }}
        />
        <BotonSecundario
          disabled={totalPesadas === 0}
          alto={56}
          tamanioTexto={19}
          titulo="Compartir historial (CSV)"
          onPress={() => void exportar()}
        />
        {totalPesadas === 0 ? (
          <Text style={styles.notaExportacion}>El CSV se habilita al guardar la primera pesada.</Text>
        ) : null}
      </View>
    </View>
  );
}

interface TarjetaAnimalProps {
  animal: AnimalConResumen;
  destacada?: boolean;
  onPress: () => void;
}

function TarjetaAnimal({ animal, destacada = false, onPress }: TarjetaAnimalProps) {
  return (
    <Pressable
      accessibilityLabel={`Ver pesadas del arete ${animal.arete}`}
      accessibilityRole="button"
      android_ripple={{ color: colors.rippleTarjeta }}
      onPress={onPress}
      style={({ pressed }) => [
        styles.tarjetaAnimal,
        destacada ? styles.tarjetaDestacada : undefined,
        pressed ? styles.tarjetaPresionada : undefined,
      ]}
    >
      <Orejera arete={animal.arete} />
      <View style={styles.datosAnimal}>
        <Text numberOfLines={1} style={styles.nombreAnimal}>
          {`Arete ${animal.arete}`}
        </Text>
        <Text numberOfLines={1} style={styles.fechaAnimal}>
          {animal.ultima_estimacion == null ? 'Sin pesadas' : fechaLegible(animal.ultima_estimacion)}
        </Text>
      </View>
      {animal.ultimo_peso_kg == null ? (
        <Text style={styles.sinPeso}>—</Text>
      ) : (
        <View style={styles.pesoBloque}>
          <View style={styles.pesoFila}>
            <Text style={styles.numeroResumen}>{Math.round(animal.ultimo_peso_kg)}</Text>
            <Text style={styles.unidadResumen}>kg</Text>
          </View>
          <DeltaAnimal animal={animal} />
        </View>
      )}
    </Pressable>
  );
}

// The reason a rancher opens the history at all: how much did this animal move.
function DeltaAnimal({ animal }: { animal: AnimalConResumen }) {
  if (animal.ultimo_peso_kg == null || animal.penultimo_peso_kg == null) {
    return <Text style={[styles.delta, styles.deltaNeutro]}>Primera pesada</Text>;
  }

  const diferencia = Math.round(animal.ultimo_peso_kg) - Math.round(animal.penultimo_peso_kg);

  if (diferencia === 0) {
    return <Text style={[styles.delta, styles.deltaNeutro]}>= igual</Text>;
  }

  const referencia =
    animal.penultima_estimacion == null ? null : fechaCorta(animal.penultima_estimacion);
  const cuerpo = `${signoPeso(diferencia)} kg${referencia == null ? '' : ` vs. ${referencia}`}`;

  return (
    <Text style={[styles.delta, diferencia > 0 ? styles.deltaSube : styles.deltaBaja]}>
      {cuerpo}
    </Text>
  );
}

function signoPeso(diferencia: number): string {
  return diferencia > 0 ? `+${diferencia}` : `\u2212${Math.abs(diferencia)}`;
}

function Orejera({ arete }: { arete: string }) {
  return (
    <View style={styles.orejera}>
      <View style={styles.agujeroOrejera} />
      <Text numberOfLines={1} style={styles.textoOrejera}>
        {arete}
      </Text>
    </View>
  );
}

interface FilaPesadaProps {
  anterior: Estimacion | null;
  estimacion: Estimacion;
  onBorrar: () => void;
}

function FilaPesada({ anterior, estimacion, onBorrar }: FilaPesadaProps) {
  return (
    <Swipeable
      overshootRight={false}
      renderRightActions={() => (
        <Pressable
          accessibilityLabel={`Borrar la pesada de las ${horaLegible(estimacion.timestamp)}`}
          accessibilityRole="button"
          onPress={onBorrar}
          style={({ pressed }) => [
            styles.panelBorrar,
            pressed ? styles.panelBorrarPresionado : undefined,
          ]}
        >
          <Text style={styles.iconoBorrar}>{'\u{1F5D1}'}</Text>
          <Text style={styles.textoBorrar}>Borrar</Text>
        </Pressable>
      )}
    >
      <View style={styles.tarjetaEstimacion}>
        <Image
          accessibilityIgnoresInvertColors={true}
          resizeMode="cover"
          source={{ uri: estimacion.ruta_foto }}
          style={styles.miniaturaPesada}
        />
        <View style={styles.datosAnimal}>
          <Text style={styles.etiquetaEstimacion}>PESO ESTIMADO</Text>
          <Text style={styles.fechaAnimal}>{fechaLegible(estimacion.timestamp)}</Text>
        </View>
        <View style={styles.pesoBloque}>
          <View style={styles.pesoFila}>
            <Text style={styles.numeroResumen}>{Math.round(estimacion.peso_kg)}</Text>
            <Text style={styles.unidadResumen}>kg</Text>
          </View>
          <DeltaPesada anterior={anterior} estimacion={estimacion} />
        </View>
      </View>
    </Swipeable>
  );
}

// Each row against the one before it; "= igual" makes duplicates obvious.
function DeltaPesada({ anterior, estimacion }: { anterior: Estimacion | null; estimacion: Estimacion }) {
  if (anterior == null) {
    return <Text style={[styles.delta, styles.deltaNeutro]}>Primera pesada</Text>;
  }

  const diferencia = Math.round(estimacion.peso_kg) - Math.round(anterior.peso_kg);

  if (diferencia === 0) {
    return <Text style={[styles.delta, styles.deltaNeutro]}>= igual</Text>;
  }

  return (
    <Text style={[styles.delta, diferencia > 0 ? styles.deltaSube : styles.deltaBaja]}>
      {`${signoPeso(diferencia)} kg`}
    </Text>
  );
}

// Header trend: the newest weighing against the one before it.
function tendenciaDesde(estimaciones: Estimacion[]): string | null {
  if (estimaciones.length < 2) {
    return null;
  }

  const diferencia = Math.round(estimaciones[0].peso_kg) - Math.round(estimaciones[1].peso_kg);

  if (diferencia === 0) {
    return `igual que ${fechaCorta(estimaciones[1].timestamp)}`;
  }

  return `${signoPeso(diferencia)} kg desde ${fechaCorta(estimaciones[1].timestamp)}`;
}

function EstadoVacio({
  mostrarRegistro = false,
  esBusqueda = false,
  onLimpiarBusqueda,
  texto,
}: {
  mostrarRegistro?: boolean;
  esBusqueda?: boolean;
  onLimpiarBusqueda?: () => void;
  texto: string;
}) {
  return (
    <View style={styles.estadoVacio}>
      <Text style={styles.estadoVacioTexto}>
        {mostrarRegistro ? 'Aún no hay pesadas guardadas.' : texto}
      </Text>
      {mostrarRegistro ? (
        <Text style={styles.estadoVacioDetalle}>Tome una foto y guarde el resultado con el arete.</Text>
      ) : null}
      {esBusqueda && onLimpiarBusqueda != null ? (
        <Pressable
          accessibilityLabel="Limpiar búsqueda"
          accessibilityRole="button"
          android_ripple={{ color: colors.rippleSecundario }}
          onPress={onLimpiarBusqueda}
          style={({ pressed }) => [
            styles.botonResetBusqueda,
            pressed ? styles.botonResetPresionado : undefined,
          ]}
        >
          <Text style={styles.textoResetBusqueda}>Limpiar búsqueda</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

function Mensaje({ texto }: { texto: string }) {
  return (
    <View style={styles.mensaje}>
      <Text style={styles.mensajeTexto}>{texto}</Text>
    </View>
  );
}

function fechaLegible(timestamp: string): string {
  const fecha = new Date(timestamp);
  if (Number.isNaN(fecha.getTime())) {
    return timestamp;
  }

  const diferenciaDias = diferenciaEnDias(fecha);
  const hora = fecha.toLocaleTimeString('es-GT', { hour: 'numeric', minute: '2-digit' });

  if (diferenciaDias === 0) {
    return `Hoy, ${hora}`;
  }
  if (diferenciaDias === 1) {
    return `Ayer, ${hora}`;
  }

  return fecha.toLocaleDateString('es-GT', { day: 'numeric', month: 'long', year: 'numeric' });
}

// Short form for the delta line: "ayer", "20 ago".
function fechaCorta(timestamp: string): string {
  const fecha = new Date(timestamp);
  if (Number.isNaN(fecha.getTime())) {
    return timestamp;
  }

  const diferenciaDias = diferenciaEnDias(fecha);

  if (diferenciaDias === 0) {
    return 'hoy';
  }
  if (diferenciaDias === 1) {
    return 'ayer';
  }

  return fecha
    .toLocaleDateString('es-GT', { day: 'numeric', month: 'short' })
    .replace(/\.$/, '');
}

// Used by the delete confirmation so it names the same time the row shows.
function horaLegible(timestamp: string): string {
  const fecha = new Date(timestamp);
  if (Number.isNaN(fecha.getTime())) {
    return timestamp;
  }

  return fecha.toLocaleTimeString('es-GT', { hour: 'numeric', minute: '2-digit' });
}

function diferenciaEnDias(fecha: Date): number {
  const ahora = new Date();
  const inicioHoy = new Date(ahora.getFullYear(), ahora.getMonth(), ahora.getDate()).getTime();
  const inicioFecha = new Date(fecha.getFullYear(), fecha.getMonth(), fecha.getDate()).getTime();
  return Math.round((inicioHoy - inicioFecha) / 86_400_000);
}

const styles = StyleSheet.create({
  pantalla: {
    flex: 1,
    backgroundColor: colors.cremaFondo,
  },
  encabezado: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    paddingRight: 20,
    paddingBottom: 16,
    paddingLeft: 20,
    backgroundColor: colors.bosque,
  },
  botonVolver: {
    width: 48,
    height: 48,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 3,
    borderColor: colors.salvia,
    borderRadius: 14,
  },
  volverPresionado: {
    opacity: 0.8,
  },
  chevron: {
    marginTop: -4,
    color: colors.salvia,
    fontFamily: font.regular,
    fontSize: 36,
    lineHeight: 40,
  },
  titulosEncabezado: {
    flex: 1,
    minWidth: 0,
  },
  tituloEncabezado: {
    color: colors.crema,
    fontFamily: font.black,
    fontSize: 30,
    lineHeight: 34,
  },
  subtituloEncabezado: {
    marginTop: 2,
    color: colors.salviaClara,
    fontFamily: font.regular,
    fontSize: 16,
  },
  tendencia: {
    // This green is literal; it is the only lighter accent on bosque.
    color: '#8fe39c',
    fontFamily: font.bold,
  },
  contenidoLista: {
    flexGrow: 1,
    gap: 12,
    paddingTop: 16,
    paddingHorizontal: 16,
    paddingBottom: 8,
  },
  tarjetaAnimal: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 16,
    minHeight: 98,
    paddingVertical: 14,
    paddingHorizontal: 16,
    borderWidth: 1,
    borderColor: colors.bordeTarjeta,
    borderRadius: radius.tarjeta,
    backgroundColor: colors.tarjeta,
  },
  tarjetaDestacada: {
    borderWidth: 2,
    borderColor: colors.maiz,
  },
  tarjetaPresionada: {
    opacity: 0.84,
  },
  orejera: {
    width: 76,
    height: 70,
    alignItems: 'center',
    justifyContent: 'flex-end',
    paddingBottom: 10,
    borderTopLeftRadius: 10,
    borderTopRightRadius: 10,
    borderBottomRightRadius: 14,
    borderBottomLeftRadius: 14,
    backgroundColor: colors.maiz,
  },
  agujeroOrejera: {
    position: 'absolute',
    top: 7,
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: colors.cremaFondo,
  },
  textoOrejera: {
    width: '100%',
    paddingHorizontal: 3,
    color: colors.bosque,
    fontFamily: font.black,
    fontSize: 18,
    letterSpacing: -0.3,
    textAlign: 'center',
  },
  datosAnimal: {
    flex: 1,
    minWidth: 0,
  },
  nombreAnimal: {
    color: colors.verdeNombre,
    fontFamily: font.bold,
    fontSize: 20,
    lineHeight: 25,
  },
  fechaAnimal: {
    marginTop: 2,
    color: colors.tierra,
    fontFamily: font.regular,
    fontSize: 15,
    lineHeight: 20,
  },
  pesoBloque: {
    alignItems: 'flex-end',
  },
  pesoFila: {
    flexDirection: 'row',
    alignItems: 'baseline',
    gap: 4,
  },
  delta: {
    fontFamily: font.bold,
    fontSize: 15,
    lineHeight: 18,
  },
  deltaSube: {
    color: colors.exito,
  },
  deltaBaja: {
    color: colors.error,
  },
  deltaNeutro: {
    color: colors.grisCalido,
  },
  numeroResumen: {
    color: colors.verdeTinta,
    fontFamily: font.black,
    fontSize: 30,
    lineHeight: 36,
  },
  unidadResumen: {
    color: colors.tierra,
    fontFamily: font.bold,
    fontSize: 16,
  },
  sinPeso: {
    color: colors.grisCalido,
    fontFamily: font.black,
    fontSize: 30,
  },
  tarjetaEstimacion: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 16,
    minHeight: 92,
    paddingVertical: 14,
    paddingHorizontal: 16,
    borderWidth: 1,
    borderColor: colors.bordeTarjeta,
    borderRadius: radius.tarjeta,
    backgroundColor: colors.tarjeta,
  },
  miniaturaPesada: {
    width: 62,
    height: 62,
    borderRadius: 14,
    backgroundColor: colors.bosqueCamara,
  },
  panelBorrar: {
    width: 104 + radius.tarjeta,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 4,
    marginLeft: -radius.tarjeta,
    paddingLeft: radius.tarjeta,
    borderRadius: radius.tarjeta,
    backgroundColor: colors.error,
  },
  panelBorrarPresionado: {
    opacity: 0.85,
  },
  iconoBorrar: {
    color: colors.crema,
    fontFamily: font.regular,
    fontSize: 22,
    lineHeight: 26,
  },
  textoBorrar: {
    color: colors.crema,
    fontFamily: font.bold,
    fontSize: 15,
  },
  ayudaBorrado: {
    paddingTop: 4,
    color: colors.tierra,
    fontFamily: font.regular,
    fontSize: 15,
    lineHeight: 18,
    textAlign: 'center',
  },
  etiquetaEstimacion: {
    color: colors.tierra,
    fontFamily: font.bold,
    fontSize: 15,
    letterSpacing: 1.0,
  },
  estadoVacio: {
    flex: 1,
    alignItems: 'flex-start',
    justifyContent: 'flex-start',
    paddingTop: 20,
    paddingHorizontal: 4,
  },
  estadoVacioTexto: {
    color: colors.verdeTinta,
    fontFamily: font.bold,
    fontSize: 20,
    lineHeight: 26,
  },
  estadoVacioDetalle: {
    marginTop: 4,
    color: colors.tierra,
    fontFamily: font.regular,
    fontSize: 15,
    lineHeight: 21,
  },
  mensaje: {
    paddingVertical: 12,
    paddingHorizontal: 14,
    borderWidth: 1,
    borderColor: colors.bordeTarjeta,
    borderRadius: 14,
    backgroundColor: colors.tarjeta,
  },
  mensajeTexto: {
    color: colors.verdeTinta,
    fontFamily: font.medium,
    fontSize: 16,
    lineHeight: 22,
  },
  banda: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    minHeight: 48,
    marginTop: 12,
    marginHorizontal: 16,
    paddingVertical: 10,
    paddingHorizontal: 14,
    borderRadius: 14,
    backgroundColor: colors.exito,
  },
  bandaIcono: {
    width: 24,
    height: 24,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 12,
    backgroundColor: colors.crema,
  },
  bandaCheck: {
    color: colors.exito,
    fontFamily: font.black,
    fontSize: 15,
  },
  bandaTexto: {
    flex: 1,
    color: colors.crema,
    fontFamily: font.bold,
    fontSize: 16,
    lineHeight: 21,
  },
  busquedaContenedor: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderBottomWidth: 1,
    borderBottomColor: colors.bordeTarjeta,
    backgroundColor: colors.cremaFondo,
  },
  lupaIcono: {
    color: colors.tierra,
    fontFamily: font.bold,
    fontSize: 22,
    lineHeight: 24,
  },
  campoBusqueda: {
    flex: 1,
    height: 44,
    paddingHorizontal: 12,
    borderWidth: 2,
    borderColor: colors.bordeTarjeta,
    borderRadius: radius.input,
    color: colors.verdeTinta,
    backgroundColor: colors.tarjeta,
    fontFamily: font.medium,
    fontSize: 16,
  },
  botonLimpiarBusqueda: {
    width: 36,
    height: 36,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 10,
    backgroundColor: colors.chipClaro,
  },
  botonLimpiarPresionado: {
    opacity: 0.7,
  },
  textoLimpiarBusqueda: {
    color: colors.tierra,
    fontFamily: font.bold,
    fontSize: 16,
  },
  botonResetBusqueda: {
    marginTop: 14,
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderWidth: 2,
    borderColor: colors.verdeMedio,
    borderRadius: radius.input,
    backgroundColor: 'transparent',
  },
  botonResetPresionado: {
    opacity: 0.8,
  },
  textoResetBusqueda: {
    color: colors.verdeMedio,
    fontFamily: font.bold,
    fontSize: 15,
  },
  pie: {
    gap: 10,
    paddingTop: 12,
    paddingHorizontal: 16,
    borderTopWidth: 1,
    borderTopColor: colors.bordeTarjeta,
    backgroundColor: colors.cremaFondo,
  },
  notaExportacion: {
    color: colors.tierra,
    fontFamily: font.regular,
    fontSize: 15,
    lineHeight: 20,
    textAlign: 'center',
  },
});
