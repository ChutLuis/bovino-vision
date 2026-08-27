import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';

import { CapturaScreen } from '../screens/CapturaScreen';
import { HistorialScreen } from '../screens/HistorialScreen';
import { ProcesandoScreen } from '../screens/ProcesandoScreen';
import { ResultadoScreen } from '../screens/ResultadoScreen';
import { SplashScreen } from '../screens/SplashScreen';
import type { RootStackParamList } from './types';

const Stack = createNativeStackNavigator<RootStackParamList>();

export function AppNavigator() {
  return (
    <NavigationContainer>
      <Stack.Navigator initialRouteName="Splash" screenOptions={{ headerShown: false }}>
        <Stack.Screen name="Splash" component={SplashScreen} />
        <Stack.Screen name="Captura" component={CapturaScreen} />
        <Stack.Screen name="Procesando" component={ProcesandoScreen} />
        <Stack.Screen name="Resultado" component={ResultadoScreen} />
        <Stack.Screen name="Historial" component={HistorialScreen} />
      </Stack.Navigator>
    </NavigationContainer>
  );
}
