import { StyleSheet, View } from 'react-native';

import { AppText } from '@/components/ui';
import { colors, radii, spacing } from '@/theme';

type ConfidenceIndicatorProps = { value: number };

export function ConfidenceIndicator({ value }: ConfidenceIndicatorProps) {
  const confidence = Math.round(Math.min(100, Math.max(0, value)));

  return (
    <View
      accessibilityLabel={`Confiança da interpretação: ${confidence}%`}
      accessibilityRole="progressbar"
      accessibilityValue={{ min: 0, max: 100, now: confidence }}
      style={styles.container}
    >
      <View style={styles.labelRow}>
        <AppText tone="secondary" variant="supporting">
          Confiança da interpretação
        </AppText>
        <AppText style={styles.value} variant="cardTitle">
          {confidence}%
        </AppText>
      </View>
      <View style={styles.track}>
        <View style={[styles.progress, { width: `${confidence}%` }]} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { gap: spacing.sm },
  labelRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  value: { fontSize: 14, lineHeight: 20 },
  track: {
    height: 6,
    overflow: 'hidden',
    borderRadius: radii.full,
    backgroundColor: colors.accentSoft,
  },
  progress: {
    height: '100%',
    borderRadius: radii.full,
    backgroundColor: colors.accent,
  },
});
