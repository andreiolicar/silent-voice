import type { LucideIcon } from 'lucide-react-native';
import { useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  View,
  type PressableProps,
  type StyleProp,
  type TextStyle,
  type ViewStyle,
} from 'react-native';

import { useReducedMotion } from '@/hooks/useReducedMotion';
import {
  colors,
  focusRing,
  getWebTransitionStyle,
  isFocusVisible,
  radii,
  spacing,
} from '@/theme';

import { AppText } from './AppText';

type ButtonVariant = 'primary' | 'ghost' | 'danger';

type ButtonProps = Omit<PressableProps, 'children' | 'style'> & {
  label: string;
  variant?: ButtonVariant;
  loading?: boolean;
  leftIcon?: LucideIcon;
  rightIcon?: LucideIcon;
  labelStyle?: StyleProp<TextStyle>;
  contentStyle?: StyleProp<ViewStyle>;
  iconSize?: number;
  leftIconBackgroundColor?: string;
  leftIconContainerSize?: number;
  foregroundColor?: string;
  style?: StyleProp<ViewStyle>;
};

export function Button({
  disabled = false,
  accessibilityLabel,
  onBlur,
  onFocus,
  onHoverIn,
  onHoverOut,
  label,
  labelStyle,
  contentStyle,
  iconSize = 18,
  leftIconBackgroundColor,
  leftIconContainerSize = 26,
  foregroundColor,
  leftIcon: LeftIcon,
  loading = false,
  rightIcon: RightIcon,
  style,
  variant = 'primary',
  ...props
}: ButtonProps) {
  const [focused, setFocused] = useState(false);
  const [hovered, setHovered] = useState(false);
  const reduceMotion = useReducedMotion();
  const isDisabled = disabled || loading;
  const foreground =
    foregroundColor ??
    (variant === 'primary'
      ? colors.white
      : variant === 'danger'
        ? colors.error
        : colors.primary);

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel ?? label}
      accessibilityState={{ busy: loading, disabled: isDisabled }}
      disabled={isDisabled}
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
        styles[variant],
        getWebTransitionStyle(
          reduceMotion,
          'background-color, border-color, opacity',
        ),
        hovered && styles[`${variant}Hovered`],
        focused && focusRing,
        pressed && styles.pressed,
        isDisabled && styles.disabled,
        style,
      ]}
      {...props}
    >
      {loading ? (
        <ActivityIndicator color={foreground} size="small" />
      ) : (
        <View style={[styles.content, contentStyle]}>
          {LeftIcon ? (
            leftIconBackgroundColor ? (
              <View
                style={[
                  styles.leftIconContainer,
                  {
                    width: leftIconContainerSize,
                    height: leftIconContainerSize,
                    backgroundColor: leftIconBackgroundColor,
                  },
                ]}
              >
                <LeftIcon color={foreground} size={iconSize} />
              </View>
            ) : (
              <LeftIcon color={foreground} size={iconSize} />
            )
          ) : null}
          <AppText
            style={labelStyle}
            tone={
              variant === 'primary'
                ? 'inverse'
                : variant === 'danger'
                  ? 'error'
                  : 'primary'
            }
            variant="button"
          >
            {label}
          </AppText>
          {RightIcon ? <RightIcon color={foreground} size={iconSize} /> : null}
        </View>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    minHeight: 48,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: spacing.lgPlus,
    borderRadius: radii.control,
    borderWidth: 1,
    borderColor: 'transparent',
  },
  primary: { backgroundColor: colors.accent },
  ghost: { backgroundColor: 'transparent' },
  danger: {
    backgroundColor: colors.errorSoft,
    borderColor: 'rgba(196, 61, 77, 0.32)',
  },
  primaryHovered: { opacity: 0.9 },
  ghostHovered: {
    backgroundColor: colors.accentSoft,
    borderColor: colors.accent,
  },
  dangerHovered: { opacity: 0.84 },
  content: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.sm,
  },
  leftIconContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: radii.full,
  },
  pressed: { opacity: 0.76 },
  disabled: { opacity: 0.45 },
});
