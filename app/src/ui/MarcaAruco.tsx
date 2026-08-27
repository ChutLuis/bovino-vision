import { StyleSheet, View } from 'react-native';

import { colors } from './theme';

interface MarcaArucoProps {
  size: number;
  borderWidth?: number;
}

const CELDAS = Array.from({ length: 16 }, (_, index) => {
  const fila = Math.floor(index / 4);
  const columna = index % 4;
  return (fila + columna) % 2 === 0;
});

export function MarcaAruco({ size, borderWidth }: MarcaArucoProps) {
  const radio = Math.max(6, Math.round(size / 9));
  const grosorBorde = borderWidth ?? radio;

  return (
    <View
      style={[
        styles.marca,
        {
          width: size,
          height: size,
          borderWidth: grosorBorde,
          borderRadius: radio,
        },
      ]}
    >
      <View style={styles.cuadricula}>
        {CELDAS.map((esMaiz, index) => (
          <View key={index} style={[styles.celda, esMaiz ? styles.celdaMaiz : undefined]} />
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  marca: {
    borderColor: colors.maiz,
    overflow: 'hidden',
  },
  cuadricula: {
    flex: 1,
    flexDirection: 'row',
    flexWrap: 'wrap',
  },
  celda: {
    width: '25%',
    height: '25%',
  },
  celdaMaiz: {
    backgroundColor: colors.maiz,
  },
});
