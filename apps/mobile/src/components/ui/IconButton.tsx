import type { LucideIcon } from 'lucide-react-native';
import { useState } from 'react';
import {
  Pressable,
  StyleSheet,
  type PressableProps,
  type StyleProp,
  type ViewStyle,
} from 'react-native';

import { useReducedMotion } from '@/hooks/useReducedMotion';
import {
  colors,
  focusRing,
  getWebTransitionStyle,
  isFocusVisible,
  radii,
} from '@/theme';

type IconButtonVariant = 'surface' | 'ghost' | 'accent' | 'refresh';

type IconButtonProps = Omit<PressableProps, 'children' | 'style'> & {
  accessibilityLabel: string;
  icon: LucideIcon;
  iconSize?: number;
  size?: 'compact' | 'medium' | 'large';
  style?: StyleProp<ViewStyle>;
  variant?: IconButtonVariant;
};

export function IconButton({
  accessibilityLabel,
  disabled,
  icon: Icon,
  iconSize: customIconSize,
  onBlur,
  onFocus,
  onHoverIn,
  onHoverOut,
  size = 'medium',
  style,
  variant = 'surface',
  ...props
}: IconButtonProps) {
  const [focused, setFocused] = useState(false);
  const [hovered, setHovered] = useState(false);
  const reduceMotion = useReducedMotion();
  const iconColor =
    variant === 'accent'
      ? colors.white
      : variant === 'refresh'
        ? colors.accent
        : colors.primary;
  const iconSize =
    customIconSize ?? (size === 'compact' ? 14 : size === 'large' ? 22 : 20);

  return (
    <Pressable
      accessibilityLabel={accessibilityLabel}
      accessibilityRole="button"
      accessibilityState={{ disabled: Boolean(disabled) }}
      disabled={Boolean(disabled)}
      hitSlop={size === 'compact' ? 10 : 4}
      onBlur={(event) => {
        setFocused(false);
        onBlur?.(event);
      }}
      onFocus={(event) => {
        setFocused(isFocusVisible(event));
        onFocus?.(event);
      }}
      onHoverIn={(event) => {
        setHovered(true);
        onHoverIn?.(event);
      }}
      onHoverOut={(event) => {
        setHovered(false);
        onHoverOut?.(event);
      }}
      style={({ pressed }) => [
        styles.base,
        styles[size],
        styles[variant],
        getWebTransitionStyle(
          reduceMotion,
          'background-color, border-color, opacity',
        ),
        hovered && styles[`${variant}Hovered`],
        focused && focusRing,
        pressed && styles.pressed,
        disabled && styles.disabled,
        style,
      ]}
      {...props}
    >
      <Icon color={iconColor} size={iconSize} />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: radii.full,
    borderWidth: 1,
    borderColor: 'transparent',
  },
  medium: { width: 44, height: 44 },
  large: { width: 52, height: 52 },
  compact: { width: 24, height: 24 },
  surface: { backgroundColor: colors.surface },
  ghost: { backgroundColor: 'transparent' },
  accent: { backgroundColor: colors.accent },
  refresh: { backgroundColor: 'transparent', borderWidth: 0 },
  surfaceHovered: {
    backgroundColor: colors.accentSoft,
  },
  ghostHovered: { backgroundColor: colors.accentSoft },
  accentHovered: { opacity: 0.88 },
  refreshHovered: { opacity: 0.72 },
  pressed: { opacity: 0.7 },
  disabled: { opacity: 0.45 },
});
