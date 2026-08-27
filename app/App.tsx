import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { AppNavigator } from './src/navigation/AppNavigator';
import { ModeloProvider } from './src/providers/ModelProvider';

export default function App() {
  return (
    <SafeAreaProvider>
      <ModeloProvider>
        <AppNavigator />
      </ModeloProvider>
      <StatusBar style="light" />
    </SafeAreaProvider>
  );
}
