import { useCallback, useEffect } from 'react';
import {
  useAnimatedStyle,
  useSharedValue,
  withTiming,
} from 'react-native-reanimated';

import { useReducedMotion } from '@/hooks/useReducedMotion';
import { motion } from '@/theme/motion';

export function usePressScale(targetScale: number) {
  const reduceMotion = useReducedMotion();
  const scale = useSharedValue(1);
  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ scale: scale.value }],
  }));

  const pressIn = useCallback(() => {
    scale.set(
      withTiming(reduceMotion ? 1 : targetScale, {
        duration: reduceMotion ? 0 : motion.press,
        easing: motion.easing,
      }),
    );
  }, [reduceMotion, scale, targetScale]);

  const pressOut = useCallback(() => {
    scale.set(
      withTiming(1, {
        duration: reduceMotion ? 0 : motion.press,
        easing: motion.easing,
      }),
    );
  }, [reduceMotion, scale]);

  useEffect(() => {
    if (reduceMotion) scale.set(1);
  }, [reduceMotion, scale]);

  return { animatedStyle, pressIn, pressOut };
}
