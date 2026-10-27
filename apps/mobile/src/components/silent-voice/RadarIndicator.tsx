import type { LucideIcon } from 'lucide-react-native';
import { StyleSheet, View } from 'react-native';

import { colors, radii } from '@/theme';

type RadarIndicatorProps = {
  accessibilityLabel: string;
  active?: boolean;
  center?: 'dot' | 'icon' | 'none';
  icon?: LucideIcon;
  rings?: 2 | 3 | 4;
  size?: number;
};

export function RadarIndicator({
  accessibilityLabel,
  active = true,
  center,
  icon: Icon,
  rings = 2,
  size = 112,
}: RadarIndicatorProps) {
  const color = active ? colors.accent : colors.textSecondary;
  const resolvedCenter = center ?? (Icon ? 'icon' : 'dot');
  const ringSizes = {
    2: [100, 72],
    3: [100, 72, 45],
    4: [100, 79, 57, 36],
  }[rings];

  return (
    <View
      accessibilityLabel={accessibilityLabel}
      accessibilityRole="image"
      style={[styles.outer, { width: size, height: size }]}
    >
      {ringSizes.map((ringSize, index) => (
        <View
          key={ringSize}
          style={[
            styles.ring,
            {
              width: `${ringSize}%`,
              height: `${ringSize}%`,
              borderColor: color,
              backgroundColor:
                resolvedCenter === 'icon'
                  ? active
                    ? colors.accentSoft
                    : colors.background
                  : 'transparent',
              opacity: 0.35 + index * 0.15,
            },
          ]}
        />
      ))}
      {resolvedCenter === 'icon' && Icon ? (
        <View style={[styles.iconCenter, { backgroundColor: color }]}>
          <Icon color={colors.white} size={Math.round(size * 0.24)} />
        </View>
      ) : null}
      {resolvedCenter === 'dot' ? (
        <View
          style={[
            styles.dot,
            {
              width: Math.max(5, Math.round(size * 0.08)),
              height: Math.max(5, Math.round(size * 0.08)),
              backgroundColor: color,
            },
          ]}
        />
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  outer: { alignItems: 'center', justifyContent: 'center' },
  ring: {
    position: 'absolute',
    borderWidth: 0.5,
    borderRadius: radii.full,
  },
  iconCenter: {
    width: '48%',
    height: '48%',
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: radii.full,
  },
  dot: { borderRadius: radii.full },
});
