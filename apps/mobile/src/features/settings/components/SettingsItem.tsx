import { ChevronRight, type LucideIcon } from 'lucide-react-native';
import { useState } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';

import { AppText, Toggle } from '@/components/ui';
import {
  colors,
  focusRing,
  isFocusVisible,
  radii,
  spacing,
  webNoOutline,
} from '@/theme';

type SettingsItemProps = {
  description?: string;
  icon: LucideIcon;
  onPress?: () => void;
  onValueChange?: (value: boolean) => void;
  showDivider?: boolean;
  title: string;
  type: 'navigation' | 'toggle';
  value?: boolean;
};

export function SettingsItem({
  description,
  icon: Icon,
  onPress,
  onValueChange,
  showDivider = false,
  title,
  type,
  value = false,
}: SettingsItemProps) {
  const [focused, setFocused] = useState(false);
  const content = (
    <View style={[styles.row, showDivider && styles.divider]}>
      <View style={styles.iconFrame}>
        <Icon color={colors.accent} size={20} strokeWidth={1.8} />
      </View>
      <View style={styles.copy}>
        <AppText variant="cardTitle">{title}</AppText>
        {description ? (
          <AppText tone="secondary" variant="caption">
            {description}
          </AppText>
        ) : null}
      </View>
      {type === 'toggle' && onValueChange ? (
        <Toggle
          accessibilityLabel={title}
          onValueChange={onValueChange}
          size="compact"
          value={value}
        />
      ) : (
        <ChevronRight
          color={onPress ? colors.textSecondary : colors.disabled}
          size={18}
        />
      )}
    </View>
  );

  if (!onPress) return content;

  return (
    <Pressable
      accessibilityLabel={title}
      accessibilityRole="button"
      onBlur={() => setFocused(false)}
      onFocus={(event) => setFocused(isFocusVisible(event))}
      onPress={onPress}
      style={({ pressed }) => [
        webNoOutline,
        focused && focusRing,
        pressed && styles.pressed,
      ]}
    >
      {content}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  pressed: { opacity: 0.76 },
  row: {
    minHeight: 58,
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    marginHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  divider: { borderTopWidth: 1, borderTopColor: colors.border },
  iconFrame: {
    width: 34,
    height: 34,
    flexShrink: 0,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: radii.full,
    backgroundColor: colors.background,
  },
  copy: { minWidth: 0, flex: 1, gap: spacing.xxs },
});
