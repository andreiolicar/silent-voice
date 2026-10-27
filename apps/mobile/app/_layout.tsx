import { Manrope_400Regular } from '@expo-google-fonts/manrope/400Regular';
import { Manrope_500Medium } from '@expo-google-fonts/manrope/500Medium';
import { Manrope_600SemiBold } from '@expo-google-fonts/manrope/600SemiBold';
import { Manrope_700Bold } from '@expo-google-fonts/manrope/700Bold';
import { useFonts } from 'expo-font';
import { Stack } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { useEffect } from 'react';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { IdentityBoundary } from '@/features/auth/IdentityBoundary';
import { AuthProvider, useAuth } from '@/features/auth/AuthProvider';

void SplashScreen.preventAutoHideAsync();

export default function RootLayout() {
  const [fontsLoaded, fontError] = useFonts({
    Manrope_400Regular,
    Manrope_500Medium,
    Manrope_600SemiBold,
    Manrope_700Bold,
  });

  useEffect(() => {
    if (fontsLoaded) {
      void SplashScreen.hideAsync();
    }
  }, [fontsLoaded]);

  if (fontError) throw fontError;
  if (!fontsLoaded) return null;

  return (
    <SafeAreaProvider>
      <AuthProvider>
        <AuthenticatedStack />
      </AuthProvider>
    </SafeAreaProvider>
  );
}

function AuthenticatedStack() {
  const { ready, session, onboarding } = useAuth();
  if (!ready) return null;
  return (
    <IdentityBoundary identityKey={session?.user.id || 'guest'}>
      <Stack screenOptions={{ headerShown: false }}>
        <Stack.Screen name="index" />
        <Stack.Screen name="auth" />
        <Stack.Protected guard={!onboarding}>
          <Stack.Screen name="onboarding" />
        </Stack.Protected>
        <Stack.Protected guard={Boolean(session)}>
          <Stack.Screen name="permissions" />
          <Stack.Screen name="connection" />
          <Stack.Screen name="calibration" />
          <Stack.Screen name="(main)" />
          <Stack.Screen name="playground" />
          <Stack.Screen name="account" />
        </Stack.Protected>
      </Stack>
    </IdentityBoundary>
  );
}
