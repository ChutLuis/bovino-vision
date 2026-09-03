import type { NativeStackScreenProps } from '@react-navigation/native-stack';

import type { FotoEntrada, ResultadoEstimacion } from '../domain/types';

export interface PesadaGuardada {
  arete: string;
  pesoKg: number;
}

export type RootStackParamList = {
  Splash: undefined;
  Onboarding: undefined;
  Captura: { aretePrellenado?: string; abrirGaleria?: boolean } | undefined;
  Procesando: { foto: FotoEntrada; aretePrellenado?: string };
  Resultado: { resultado: ResultadoEstimacion; aretePrellenado?: string };
  Historial: { guardado?: PesadaGuardada } | undefined;
};

export type SplashScreenProps = NativeStackScreenProps<RootStackParamList, 'Splash'>;
export type OnboardingScreenProps = NativeStackScreenProps<RootStackParamList, 'Onboarding'>;
export type CapturaScreenProps = NativeStackScreenProps<RootStackParamList, 'Captura'>;
export type ProcesandoScreenProps = NativeStackScreenProps<RootStackParamList, 'Procesando'>;
export type ResultadoScreenProps = NativeStackScreenProps<RootStackParamList, 'Resultado'>;
export type HistorialScreenProps = NativeStackScreenProps<RootStackParamList, 'Historial'>;
