import { StyleSheet, View } from 'react-native';

import { AppText } from '@/components/ui';
import type { CalibrationStep } from '@/domain/calibration';
import { colors, radii, spacing } from '@/theme';

import { calibrationOperationalSteps } from '../data/calibration.mock';

type CalibrationProgressProps = {
  step: CalibrationStep;
};

export function CalibrationProgress({ step }: CalibrationProgressProps) {
  const isComplete = step === 'complete';
  const currentIndex = isComplete
    ? calibrationOperationalSteps.length
    : calibrationOperationalSteps.indexOf(step) + 1;
  const label = isComplete
    ? 'Calibração concluída'
    : `Etapa ${currentIndex} de ${calibrationOperationalSteps.length}`;

  return (
    <View
      accessibilityLabel={label}
      accessibilityRole="progressbar"
      accessibilityValue={{
        max: calibrationOperationalSteps.length,
        min: 1,
        now: currentIndex,
        text: label,
      }}
      style={styles.container}
    >
      <AppText tone={isComplete ? 'accent' : 'secondary'} variant="label">
        {label}
      </AppText>
      <View style={styles.segments}>
        {calibrationOperationalSteps.map((candidate, index) => (
          <View
            key={candidate}
            style={[
              styles.segment,
              index < currentIndex && styles.segmentComplete,
            ]}
          />
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { gap: spacing.sm },
  segments: { flexDirection: 'row', gap: spacing.xs },
  segment: {
    height: 4,
    flex: 1,
    borderRadius: radii.full,
    backgroundColor: colors.border,
  },
  segmentComplete: { backgroundColor: colors.accent },
});
