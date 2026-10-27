import { Text, type TextProps } from 'react-native';

import { colors, typography, type TypographyVariant } from '@/theme';

const textColors = {
  primary: colors.textPrimary,
  secondary: colors.textSecondary,
  accent: colors.accent,
  inverse: colors.white,
  error: colors.error,
} as const;

type AppTextProps = TextProps & {
  tone?: keyof typeof textColors;
  variant?: TypographyVariant;
};

export function AppText({
  children,
  style,
  tone = 'primary',
  variant = 'body',
  ...props
}: AppTextProps) {
  return (
    <Text
      {...props}
      style={[{ color: textColors[tone] }, typography[variant], style]}
    >
      {children}
    </Text>
  );
}
