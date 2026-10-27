import { useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { Animated, Platform, StyleSheet } from 'react-native';

import {
  BrandLogo,
  InitialFlowScreen,
} from '@/features/initial-flow/components';
import { useReducedMotion } from '@/hooks/useReducedMotion';

const splashBackground = require('@/assets/images/initial-flow/splash-background.png');

export default function Splash() {
  const router = useRouter();
  const reduceMotion = useReducedMotion();
  const [opacity] = useState(() => new Animated.Value(1));

  useEffect(() => {
    const timeout = setTimeout(
      () => {
        Animated.timing(opacity, {
          toValue: 0,
          duration: reduceMotion ? 0 : 180,
          useNativeDriver: Platform.OS !== 'web',
        }).start(() => router.replace('./onboarding'));
      },
      reduceMotion ? 850 : 1150,
    );

    return () => clearTimeout(timeout);
  }, [opacity, reduceMotion, router]);

  return (
    <InitialFlowScreen
      background={splashBackground}
      contentStyle={styles.screen}
      scroll={false}
    >
      <Animated.View style={[styles.logo, { opacity }]}>
        <BrandLogo large />
      </Animated.View>
    </InitialFlowScreen>
  );
}

const styles = StyleSheet.create({
  screen: { alignItems: 'center', justifyContent: 'center' },
  logo: { alignItems: 'center', justifyContent: 'center' },
});
