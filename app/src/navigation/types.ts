import type { NativeStackScreenProps } from '@react-navigation/native-stack';

import type { FotoEntrada, ResultadoEstimacion } from '../domain/types';

export type RootStackParamList = {
  Splash: undefined;
  Captura: undefined;
  Procesando: { foto: FotoEntrada };
  Resultado: { resultado: ResultadoEstimacion };
  Historial: undefined;
};

export type SplashScreenProps = NativeStackScreenProps<RootStackParamList, 'Splash'>;
export type CapturaScreenProps = NativeStackScreenProps<RootStackParamList, 'Captura'>;
export type ProcesandoScreenProps = NativeStackScreenProps<RootStackParamList, 'Procesando'>;
export type ResultadoScreenProps = NativeStackScreenProps<RootStackParamList, 'Resultado'>;
export type HistorialScreenProps = NativeStackScreenProps<RootStackParamList, 'Historial'>;
