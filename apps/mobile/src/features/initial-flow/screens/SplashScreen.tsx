import { useAuth } from '@/features/auth/AuthProvider';
import { useRouter } from 'expo-router';
import { useEffect } from 'react';
import { StyleSheet } from 'react-native';
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withTiming,
} from 'react-native-reanimated';

import {
  BrandLogo,
  InitialFlowScreen,
} from '@/features/initial-flow/components';
import { useReducedMotion } from '@/hooks/useReducedMotion';
import { motion } from '@/theme';

const splashBackground = require('@/assets/images/initial-flow/splash-background.png');

export default function Splash() {
  const router = useRouter();
  const { onboarding, session } = useAuth();
  const reduceMotion = useReducedMotion();
  const opacity = useSharedValue(1);
  const logoStyle = useAnimatedStyle(() => ({ opacity: opacity.value }));

  useEffect(() => {
    const timeout = setTimeout(
      () => {
        opacity.set(
          withTiming(0, {
            duration: reduceMotion ? 0 : motion.normal,
          }),
        );
        navigationTimer = setTimeout(
          () =>
            router.replace(
              session
                ? '/(main)/home'
                : onboarding
                  ? '/auth/login'
                  : '/onboarding',
            ),
          reduceMotion ? 0 : motion.normal,
        );
      },
      reduceMotion ? 850 : 1150,
    );

    let navigationTimer: ReturnType<typeof setTimeout>;
    return () => {
      clearTimeout(timeout);
      clearTimeout(navigationTimer);
    };
  }, [opacity, reduceMotion, router, onboarding, session]);

  return (
    <InitialFlowScreen
      animate={false}
      background={splashBackground}
      contentStyle={styles.screen}
      scroll={false}
    >
      <Animated.View style={[styles.logo, logoStyle]}>
        <BrandLogo large />
      </Animated.View>
    </InitialFlowScreen>
  );
}

const styles = StyleSheet.create({
  screen: { alignItems: 'center', justifyContent: 'center' },
  logo: { alignItems: 'center', justifyContent: 'center' },
});
