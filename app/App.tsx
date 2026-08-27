import { StatusBar } from 'expo-status-bar';

import { AppNavigator } from './src/navigation/AppNavigator';
import { ModeloProvider } from './src/providers/ModelProvider';

export default function App() {
  return (
    <ModeloProvider>
      <AppNavigator />
      <StatusBar style="auto" />
    </ModeloProvider>
  );
}
