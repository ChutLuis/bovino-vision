import { Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, radius, size, type } from './theme';

const SOMBRA_OFFSET = 3;

interface BotonProps {
  titulo: string;
  onPress: () => void;
  disabled?: boolean;
  alto?: number;
  tamanioTexto?: number;
  accessibilityLabel?: string;
}

export function BotonPrimario({
  titulo,
  onPress,
  disabled = false,
  alto = size.ctaAlto,
  accessibilityLabel,
}: BotonProps) {
  return (
    <View
      style={[
        styles.primarioContenedor,
        { height: alto + SOMBRA_OFFSET },
        disabled ? styles.deshabilitado : undefined,
      ]}
    >
      <View pointerEvents="none" style={styles.sombra} />
      <Pressable
        accessibilityLabel={accessibilityLabel ?? titulo}
        accessibilityRole="button"
        android_ripple={{ color: colors.ripplePrimario }}
        disabled={disabled}
        onPress={onPress}
        style={({ pressed }) => [
          styles.primario,
          { height: alto },
          pressed && !disabled ? styles.primarioPresionado : undefined,
        ]}
      >
        <Text style={styles.textoPrimario}>{titulo}</Text>
      </Pressable>
    </View>
  );
}

export function BotonSecundario({
  titulo,
  onPress,
  disabled = false,
  alto = size.secundarioAlto,
  tamanioTexto,
  accessibilityLabel,
}: BotonProps) {
  return (
    <Pressable
      accessibilityLabel={accessibilityLabel ?? titulo}
      accessibilityRole="button"
      android_ripple={{ color: colors.rippleSecundario }}
      disabled={disabled}
      onPress={onPress}
      style={({ pressed }) => [
        styles.secundario,
        { height: alto },
        disabled ? styles.deshabilitado : undefined,
        pressed && !disabled ? styles.secundarioPresionado : undefined,
      ]}
    >
      <Text style={[styles.textoSecundario, tamanioTexto != null ? { fontSize: tamanioTexto } : undefined]}>
        {titulo}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  primarioContenedor: {
    position: 'relative',
    width: '100%',
  },
  sombra: {
    position: 'absolute',
    top: SOMBRA_OFFSET,
    right: 0,
    bottom: 0,
    left: 0,
    borderRadius: radius.cta,
    backgroundColor: colors.maizSombra,
  },
  primario: {
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: radius.cta,
    backgroundColor: colors.maiz,
  },
  primarioPresionado: {
    transform: [{ translateY: 2 }],
  },
  textoPrimario: {
    ...type.botonPrimario,
    color: colors.bosque,
  },
  secundario: {
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 3,
    borderColor: colors.verdeMedio,
    borderRadius: radius.secundario,
    backgroundColor: 'transparent',
  },
  secundarioPresionado: {
    opacity: 0.8,
  },
  textoSecundario: {
    ...type.botonSecundario,
    color: colors.verdeMedio,
  },
  deshabilitado: {
    opacity: 0.6,
  },
});
