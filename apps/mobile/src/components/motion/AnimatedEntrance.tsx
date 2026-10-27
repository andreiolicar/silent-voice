import { useMemo, type PropsWithChildren } from 'react';
import { type StyleProp, type ViewStyle } from 'react-native';
import Animated, {
  FadeIn,
  FadeInDown,
  ReduceMotion,
} from 'react-native-reanimated';

import { useReducedMotion } from '@/hooks/useReducedMotion';
import { motion } from '@/theme/motion';

type AnimatedEntranceProps = PropsWithChildren<{
  index?: number;
  style?: StyleProp<ViewStyle>;
  variant?: 'screen' | 'section';
}>;

export function AnimatedEntrance({
  children,
  index = 0,
  style,
  variant = 'section',
}: AnimatedEntranceProps) {
  const reduceMotion = useReducedMotion();
  const entering = useMemo(() => {
    if (reduceMotion) return undefined;
    if (variant === 'screen') {
      return FadeIn.duration(motion.screen).reduceMotion(ReduceMotion.System);
    }

    return FadeInDown.withInitialValues({
      opacity: 0,
      transform: [{ translateY: motion.travel }],
    })
      .duration(motion.section)
      .delay(Math.min(Math.max(index, 0), 3) * motion.stagger)
      .reduceMotion(ReduceMotion.System);
  }, [index, reduceMotion, variant]);

  return (
    <Animated.View entering={entering} style={style}>
      {children}
    </Animated.View>
  );
}
