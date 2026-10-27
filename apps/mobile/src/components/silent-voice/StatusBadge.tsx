import { Check, type LucideIcon } from 'lucide-react-native';
import { StyleSheet, View, type StyleProp, type ViewStyle } from 'react-native';

import { colors, radii, spacing } from '@/theme';

import { AppText } from '../ui/AppText';
import type { BadgeTone } from '../ui/Badge';

type StatusBadgeProps = {
  icon?: LucideIcon;
  iconPosition?: 'end' | 'start';
  label: string;
  size?: 'compact' | 'regular';
  style?: StyleProp<ViewStyle>;
  tone?: BadgeTone;
};

const toneColors = {
  success: { foreground: colors.success, background: colors.accentSoft },
  neutral: { foreground: colors.textSecondary, background: colors.background },
  warning: { foreground: colors.warning, background: colors.warningSoft },
  error: { foreground: colors.error, background: colors.errorSoft },
} as const;

export function StatusBadge({
  icon: Icon = Check,
  iconPosition = 'start',
  label,
  size = 'regular',
  style,
  tone = 'success',
}: StatusBadgeProps) {
  const color = toneColors[tone];
  const icon = (
    <View
      style={[
        styles.icon,
        size === 'compact' && styles.compactIcon,
        { backgroundColor: color.foreground },
      ]}
    >
      <Icon
        color={colors.white}
        size={size === 'compact' ? 8 : 10}
        style={styles.iconGlyph}
        strokeWidth={3}
      />
    </View>
  );

  return (
    <View
      accessibilityLabel={label}
      style={[
        styles.container,
        size === 'compact' && styles.compact,
        { backgroundColor: color.background, borderColor: color.foreground },
        style,
      ]}
    >
      {iconPosition === 'start' ? icon : null}
      <AppText
        style={[
          { color: color.foreground },
          size === 'compact' && styles.compactText,
        ]}
        variant="badge"
      >
        {label}
      </AppText>
      {iconPosition === 'end' ? icon : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignSelf: 'flex-start',
    minHeight: 28,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.sm,
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xxs,
    borderWidth: 1,
    borderRadius: radii.control,
  },
  icon: {
    width: 16,
    height: 16,
    flexShrink: 0,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: radii.full,
  },
  iconGlyph: { alignSelf: 'center' },
  compact: {
    minHeight: 22,
    gap: spacing.sm,
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xxs,
    borderWidth: 0.4,
  },
  compactIcon: { width: 14, height: 14 },
  compactText: { fontSize: 9, lineHeight: 10 },
});
