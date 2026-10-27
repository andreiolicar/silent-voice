import { ChevronRight, type LucideIcon } from 'lucide-react-native';
import { useState } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';

import { AppText, Card } from '@/components/ui';
import {
  colors,
  focusRing,
  isFocusVisible,
  radii,
  spacing,
  webNoOutline,
} from '@/theme';

type HubResourceItemProps = {
  description: string;
  icon: LucideIcon;
  onPress?: () => void;
  title: string;
};

export function HubResourceItem({
  description,
  icon: Icon,
  onPress,
  title,
}: HubResourceItemProps) {
  const [focused, setFocused] = useState(false);
  const content = (
    <Card style={styles.card}>
      <View style={styles.iconFrame}>
        <Icon color={colors.accent} size={22} strokeWidth={1.8} />
      </View>
      <View style={styles.copy}>
        <AppText variant="cardTitle">{title}</AppText>
        <AppText tone="secondary" variant="caption">
          {description}
        </AppText>
      </View>
      {onPress ? <ChevronRight color={colors.textSecondary} size={18} /> : null}
    </Card>
  );

  if (!onPress) return content;

  return (
    <Pressable
      accessibilityLabel={`${title}. ${description}`}
      accessibilityRole="button"
      onBlur={() => setFocused(false)}
      onFocus={(event) => setFocused(isFocusVisible(event))}
      onPress={onPress}
      style={({ pressed }) => [
        styles.pressable,
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
  pressable: { borderRadius: radii.card },
  pressed: { opacity: 0.76 },
  card: {
    minHeight: 66,
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
  },
  iconFrame: {
    width: 38,
    height: 38,
    flexShrink: 0,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: radii.full,
    backgroundColor: colors.background,
  },
  copy: { minWidth: 0, flex: 1, gap: spacing.xxs },
});
