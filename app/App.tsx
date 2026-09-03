import { StatusBar } from 'expo-status-bar';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { AppNavigator } from './src/navigation/AppNavigator';
import { ModeloProvider } from './src/providers/ModelProvider';

export default function App() {
  return (
    // Swipeable in the history detail gets no touches on Android without this root.
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <ModeloProvider>
          <AppNavigator />
        </ModeloProvider>
        <StatusBar style="light" />
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}
