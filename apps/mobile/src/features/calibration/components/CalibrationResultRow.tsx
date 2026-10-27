import { Check, Circle } from 'lucide-react-native';
import { StyleSheet, View } from 'react-native';

import { AppText, Badge } from '@/components/ui';
import type { CalibrationResultState } from '@/domain/calibration';
import { colors, spacing } from '@/theme';

type CalibrationResultRowProps = {
  label: string;
  state: CalibrationResultState;
};

const resultCopy: Record<CalibrationResultState, string> = {
  adequate: 'Adequado',
  captured: 'Capturado',
  pending: 'Aguardando',
};

export function CalibrationResultRow({
  label,
  state,
}: CalibrationResultRowProps) {
  const complete = state !== 'pending';
  const Icon = complete ? Check : Circle;

  return (
    <View
      accessibilityLabel={`${label}: ${resultCopy[state]}`}
      style={styles.row}
    >
      <View style={styles.label}>
        <Icon
          color={complete ? colors.accent : colors.textSecondary}
          size={18}
          strokeWidth={complete ? 2.5 : 1.6}
        />
        <AppText variant="bodySmall">{label}</AppText>
      </View>
      <Badge size="compact" tone={complete ? 'success' : 'neutral'}>
        {resultCopy[state]}
      </Badge>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    minHeight: 38,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing.md,
  },
  label: { minWidth: 0, flex: 1, flexDirection: 'row', gap: spacing.sm },
});
