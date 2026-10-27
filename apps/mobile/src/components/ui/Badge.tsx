import type { PropsWithChildren } from 'react';
import { StyleSheet, View, type StyleProp, type ViewStyle } from 'react-native';

import { colors, radii, spacing } from '@/theme';

import { AppText } from './AppText';

export type BadgeTone = 'success' | 'neutral' | 'warning' | 'error';

type BadgeProps = PropsWithChildren<{
  size?: 'compact' | 'regular';
  style?: StyleProp<ViewStyle>;
  tone?: BadgeTone;
}>;

const toneStyles = StyleSheet.create({
  success: { backgroundColor: colors.accentSoft },
  neutral: { backgroundColor: colors.background },
  warning: { backgroundColor: colors.warningSoft },
  error: { backgroundColor: colors.errorSoft },
});

const toneText = {
  success: colors.success,
  neutral: colors.textSecondary,
  warning: colors.warning,
  error: colors.error,
} as const;

export function Badge({
  children,
  size = 'regular',
  style,
  tone = 'neutral',
}: BadgeProps) {
  return (
    <View style={[styles.base, styles[size], toneStyles[tone], style]}>
      <AppText
        style={[styles[`${size}Text`], { color: toneText[tone] }]}
        variant="badge"
      >
        {children}
      </AppText>
    </View>
  );
}

const styles = StyleSheet.create({
  base: {
    alignSelf: 'flex-start',
    justifyContent: 'center',
    borderRadius: radii.full,
  },
  regular: {
    minHeight: 24,
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xxs,
  },
  compact: { minHeight: 20, paddingHorizontal: 7, paddingVertical: 5 },
  regularText: {},
  compactText: { fontSize: 7, lineHeight: 10 },
});
