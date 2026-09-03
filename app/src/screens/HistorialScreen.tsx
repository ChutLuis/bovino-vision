import {
  FlatList,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  TextInput,
  View,
  type ListRenderItemInfo,
} from 'react-native';
import { useEffect, useState } from 'react';
import { StatusBar } from 'expo-status-bar';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import {
  listarAnimales,
  listarEstimaciones,
  listarFilasExportacion,
  type AnimalConResumen,
  type Estimacion,
} from '../data/db/dao';
import { exportarCsv } from '../data/export/csv';
import type { HistorialScreenProps } from '../navigation/types';
import { BotonPrimario, BotonSecundario } from '../ui/Botones';
import { colors, font, radius } from '../ui/theme';

export function HistorialScreen({ navigation }: HistorialScreenProps) {
  const insets = useSafeAreaInsets();
  const [animales, setAnimales] = useState<AnimalConResumen[]>([]);
  const [seleccionado, setSeleccionado] = useState<AnimalConResumen | null>(null);
  const [estimaciones, setEstimaciones] = useState<Estimacion[]>([]);
  const [cargando, setCargando] = useState(true);
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [mensajeDetalle, setMensajeDetalle] = useState<string | null>(null);
  const [busqueda, setBusqueda] = useState('');

  const cargarAnimales = async (): Promise<void> => {
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
  };

  useEffect(() => {
    void cargarAnimales();
  }, []);

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
  const subtitulo = enDetalle
    ? `${estimaciones.length} ${estimaciones.length === 1 ? 'pesada' : 'pesadas'}`
    : terminoBusqueda.length > 0
      ? `${animalesFiltrados.length} ${animalesFiltrados.length === 1 ? 'resultado' : 'resultados'}`
      : resumen;

  const volver = (): void => {
    if (enDetalle) {
      setSeleccionado(null);
      return;
    }

    navigation.popToTop();
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
          <Text
            adjustsFontSizeToFit={true}
            minimumFontScale={0.7}
            numberOfLines={1}
            style={styles.tituloEncabezado}
          >
            {titulo}
          </Text>
          <Text numberOfLines={1} style={styles.subtituloEncabezado}>
            {subtitulo}
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

      {enDetalle ? (
        <FlatList
          contentContainerStyle={styles.contenidoLista}
          data={estimaciones}
          keyExtractor={(estimacion) => String(estimacion.id)}
          ListEmptyComponent={
            <EstadoVacio texto={mensajeDetalle ?? 'Este animal todavía no tiene pesadas.'} />
          }
          renderItem={renderizarEstimacion}
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
          renderItem={({ item }) => <TarjetaAnimal animal={item} onPress={() => void seleccionarAnimal(item)} />}
          showsVerticalScrollIndicator={false}
        />
      )}

      <View style={[styles.pie, { paddingBottom: insets.bottom + 16 }]}>
        <BotonPrimario alto={70} titulo="Nueva estimación" onPress={() => navigation.popToTop()} />
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
  onPress: () => void;
}

function TarjetaAnimal({ animal, onPress }: TarjetaAnimalProps) {
  return (
    <Pressable
      accessibilityLabel={`Ver estimaciones del arete ${animal.arete}`}
      accessibilityRole="button"
      android_ripple={{ color: colors.rippleTarjeta }}
      onPress={onPress}
      style={({ pressed }) => [styles.tarjetaAnimal, pressed ? styles.tarjetaPresionada : undefined]}
    >
      <Orejera arete={animal.arete} />
      <View style={styles.datosAnimal}>
        <Text
          adjustsFontSizeToFit={true}
          minimumFontScale={0.75}
          numberOfLines={1}
          style={styles.nombreAnimal}
        >
          {`Arete ${animal.arete}`}
        </Text>
        <Text numberOfLines={1} style={styles.fechaAnimal}>
          {animal.ultima_estimacion == null ? 'Sin estimaciones' : fechaLegible(animal.ultima_estimacion)}
        </Text>
      </View>
      {animal.ultimo_peso_kg == null ? (
        <Text style={styles.sinPeso}>—</Text>
      ) : (
        <View style={styles.pesoResumen}>
          <Text style={styles.numeroResumen}>{Math.round(animal.ultimo_peso_kg)}</Text>
          <Text style={styles.unidadResumen}>kg</Text>
        </View>
      )}
    </Pressable>
  );
}

function Orejera({ arete }: { arete: string }) {
  return (
    <View style={styles.orejera}>
      <View style={styles.agujeroOrejera} />
      <Text
        adjustsFontSizeToFit={true}
        minimumFontScale={0.5}
        numberOfLines={1}
        style={styles.textoOrejera}
      >
        {arete}
      </Text>
    </View>
  );
}

function renderizarEstimacion({ item }: ListRenderItemInfo<Estimacion>) {
  return (
    <View style={styles.tarjetaEstimacion}>
      <View style={styles.iconoPesada}>
        <Text style={styles.iconoPesadaTexto}>kg</Text>
      </View>
      <View style={styles.datosAnimal}>
        <Text style={styles.etiquetaEstimacion}>PESO REGISTRADO</Text>
        <Text style={styles.fechaAnimal}>{fechaLegible(item.timestamp)}</Text>
      </View>
      <View style={styles.pesoResumen}>
        <Text style={styles.numeroResumen}>{Math.round(item.peso_kg)}</Text>
        <Text style={styles.unidadResumen}>kg</Text>
      </View>
    </View>
  );
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

  const ahora = new Date();
  const inicioHoy = new Date(ahora.getFullYear(), ahora.getMonth(), ahora.getDate()).getTime();
  const inicioFecha = new Date(fecha.getFullYear(), fecha.getMonth(), fecha.getDate()).getTime();
  const diferenciaDias = Math.round((inicioHoy - inicioFecha) / 86_400_000);
  const hora = fecha.toLocaleTimeString('es-GT', { hour: 'numeric', minute: '2-digit' });

  if (diferenciaDias === 0) {
    return `Hoy, ${hora}`;
  }
  if (diferenciaDias === 1) {
    return `Ayer, ${hora}`;
  }

  return fecha.toLocaleDateString('es-GT', { day: 'numeric', month: 'long', year: 'numeric' });
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
  tarjetaPresionada: {
    opacity: 0.84,
  },
  orejera: {
    width: 62,
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
    fontSize: 23,
    textAlign: 'center',
  },
  datosAnimal: {
    flex: 1,
    minWidth: 0,
  },
  nombreAnimal: {
    color: colors.verdeNombre,
    fontFamily: font.bold,
    fontSize: 22,
    lineHeight: 27,
  },
  fechaAnimal: {
    marginTop: 2,
    color: colors.tierra,
    fontFamily: font.regular,
    fontSize: 15,
    lineHeight: 20,
  },
  pesoResumen: {
    flexDirection: 'row',
    alignItems: 'baseline',
    gap: 4,
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
  iconoPesada: {
    width: 62,
    height: 62,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 14,
    backgroundColor: colors.chipClaro,
  },
  iconoPesadaTexto: {
    color: colors.tierra,
    fontFamily: font.black,
    fontSize: 20,
  },
  etiquetaEstimacion: {
    color: colors.tierra,
    fontFamily: font.bold,
    fontSize: 13,
    letterSpacing: 1.3,
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
    fontSize: 14,
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
    fontSize: 13,
    lineHeight: 18,
    textAlign: 'center',
  },
});
