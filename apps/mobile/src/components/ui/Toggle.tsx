import { Check } from 'lucide-react-native';
import { useEffect, useState } from 'react';
import { Animated, Pressable, StyleSheet } from 'react-native';

import { useReducedMotion } from '@/hooks/useReducedMotion';
import {
  colors,
  getWebTransitionStyle,
  isFocusVisible,
  motion,
  radii,
  webNoOutline,
} from '@/theme';

type ToggleProps = {
  accessibilityLabel: string;
  disabled?: boolean;
  onValueChange: (value: boolean) => void;
  value: boolean;
  size?: 'default' | 'compact';
};

export function Toggle({
  accessibilityLabel,
  disabled = false,
  onValueChange,
  size = 'default',
  value,
}: ToggleProps) {
  const [focused, setFocused] = useState(false);
  const [hovered, setHovered] = useState(false);
  const reduceMotion = useReducedMotion();
  const compact = size === 'compact';
  const [progress] = useState(() => new Animated.Value(value ? 1 : 0));

  useEffect(() => {
    const animation = Animated.timing(progress, {
      toValue: value ? 1 : 0,
      duration: reduceMotion ? 0 : motion.toggle,
      easing: motion.easing,
      useNativeDriver: false,
    });

    animation.start();
    return () => animation.stop();
  }, [progress, reduceMotion, value]);

  const trackColor = progress.interpolate({
    inputRange: [0, 1],
    outputRange: [compact ? colors.background : colors.disabled, colors.accent],
  });
  const thumbLeft = progress.interpolate({
    inputRange: [0, 1],
    outputRange: compact ? [2, 16.5] : [3, 21],
  });

  return (
    <Pressable
      accessibilityLabel={accessibilityLabel}
      accessibilityRole="switch"
      accessibilityState={{ checked: value, disabled }}
      aria-checked={value}
      disabled={disabled}
      onBlur={() => setFocused(false)}
      onFocus={(event) => setFocused(isFocusVisible(event))}
      onHoverIn={() => setHovered(true)}
      onHoverOut={() => setHovered(false)}
      onPress={() => onValueChange(!value)}
      style={[
        styles.touchTarget,
        compact && styles.touchTargetCompact,
        webNoOutline,
        disabled && styles.disabled,
      ]}
    >
      {({ pressed }) => (
        <Animated.View
          style={[
            styles.track,
            compact && styles.trackCompact,
            { backgroundColor: trackColor },
            getWebTransitionStyle(reduceMotion, 'outline-color, opacity'),
            hovered && styles.trackHovered,
            focused && styles.trackFocused,
            pressed && styles.trackPressed,
          ]}
        >
          <Animated.View
            style={[
              styles.thumb,
              compact && styles.thumbCompact,
              { left: thumbLeft },
            ]}
          >
            <Animated.View style={{ opacity: progress }}>
              <Check
                color={colors.accent}
                size={compact ? 8 : 12}
                strokeWidth={3}
              />
            </Animated.View>
          </Animated.View>
        </Animated.View>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  touchTarget: {
    width: 52,
    height: 44,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: radii.full,
  },
  touchTargetCompact: { width: 30, height: 44 },
  track: {
    width: 42,
    height: 24,
    position: 'relative',
    borderRadius: radii.full,
  },
  trackCompact: { width: 30, height: 15.5 },
  thumb: {
    position: 'absolute',
    top: 3,
    width: 18,
    height: 18,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: radii.full,
    backgroundColor: colors.surface,
  },
  thumbCompact: { top: 2, width: 11.5, height: 11.5 },
  trackHovered: { opacity: 0.88 },
  trackFocused: {
    outlineColor: colors.primary,
    outlineStyle: 'solid',
    outlineWidth: 1,
  },
  trackPressed: { opacity: 0.72 },
  disabled: { opacity: 0.45 },
});
