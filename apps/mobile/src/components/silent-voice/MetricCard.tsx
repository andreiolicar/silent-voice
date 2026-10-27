import type { LucideIcon } from 'lucide-react-native';
import { useState } from 'react';
import {
  Pressable,
  StyleSheet,
  View,
  type StyleProp,
  type ViewStyle,
} from 'react-native';

import {
  colors,
  focusRing,
  fontFamilies,
  isFocusVisible,
  radii,
  spacing,
  webNoOutline,
} from '@/theme';

import { AppText } from '../ui/AppText';
import { Card } from '../ui/Card';

type MetricCardProps = {
  description: string;
  icon: LucideIcon;
  iconRotation?: number;
  label: string;
  onPress?: () => void;
  style?: StyleProp<ViewStyle>;
  value: string;
};

export function MetricCard({
  description,
  icon: Icon,
  iconRotation = 0,
  label,
  onPress,
  style,
  value,
}: MetricCardProps) {
  const [focused, setFocused] = useState(false);
  const card = (
    <Card
      accessibilityLabel={`${label}: ${value}. ${description}`}
      style={[styles.card, onPress ? styles.interactiveCard : style]}
    >
      <View style={styles.icon}>
        <View style={{ transform: [{ rotate: `${iconRotation}deg` }] }}>
          <Icon color={colors.accent} size={26} />
        </View>
      </View>
      <View style={styles.text}>
        <AppText style={styles.label}>{label}</AppText>
        <AppText style={styles.value} tone="accent">
          {value}
        </AppText>
        <AppText style={styles.description} tone="secondary">
          {description}
        </AppText>
      </View>
    </Card>
  );

  if (!onPress) return card;

  return (
    <Pressable
      accessibilityLabel={`${label}: ${value}. ${description}`}
      accessibilityRole="button"
      onBlur={() => setFocused(false)}
      onFocus={(event) => setFocused(isFocusVisible(event))}
      onPress={onPress}
      style={({ pressed }) => [
        styles.pressable,
        style,
        webNoOutline,
        focused && focusRing,
        pressed && styles.pressed,
      ]}
    >
      {card}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    minWidth: 150,
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.lg,
  },
  interactiveCard: { width: '100%', height: '100%' },
  pressable: {
    minWidth: 150,
    flex: 1,
    borderRadius: radii.card,
  },
  pressed: { opacity: 0.76 },
  icon: {
    width: 46,
    height: 46,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: radii.full,
    backgroundColor: colors.background,
  },
  text: { flex: 1, gap: 5 },
  label: {
    fontFamily: fontFamilies.semiBold,
    fontSize: 12,
    lineHeight: 15,
  },
  value: {
    fontFamily: fontFamilies.semiBold,
    fontSize: 16,
    lineHeight: 15,
  },
  description: {
    fontFamily: fontFamilies.medium,
    fontSize: 9,
    lineHeight: 10,
  },
});
