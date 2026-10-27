import { ChevronRight } from 'lucide-react-native';
import { Pressable, StyleSheet, View } from 'react-native';

import { AppText, Button } from '@/components/ui';
import { colors, radii, spacing, webNoOutline } from '@/theme';

type OnboardingFooterProps = {
  currentPage: 1 | 2 | 3;
  onContinue: () => void;
  onSkip: () => void;
};

export function OnboardingFooter({
  currentPage,
  onContinue,
  onSkip,
}: OnboardingFooterProps) {
  return (
    <View style={styles.container}>
      <View style={styles.buttonFrame}>
        <Button
          label="Continuar"
          labelStyle={styles.continueLabel}
          onPress={onContinue}
          style={styles.continueButton}
        />
        <ChevronRight
          color={colors.white}
          pointerEvents="none"
          size={18}
          style={styles.continueIcon}
        />
      </View>
      <Pressable
        accessibilityRole="button"
        hitSlop={8}
        onPress={onSkip}
        style={({ pressed }) => [webNoOutline, pressed && styles.pressed]}
      >
        <AppText style={styles.skip} tone="accent" variant="button">
          Pular
        </AppText>
      </Pressable>
      <View
        accessibilityLabel={`Etapa ${currentPage} de 3`}
        style={styles.dots}
      >
        {[1, 2, 3].map((page) => (
          <View
            key={page}
            style={[styles.dot, page === currentPage && styles.dotActive]}
          />
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { alignSelf: 'stretch' },
  buttonFrame: { position: 'relative' },
  continueButton: { minHeight: 43, height: 43 },
  continueLabel: { fontSize: 12, lineHeight: 22 },
  continueIcon: { position: 'absolute', top: 12, right: 35 },
  skip: {
    minHeight: 22,
    marginTop: spacing.sm,
    fontSize: 12,
    lineHeight: 22,
    textAlign: 'center',
    textAlignVertical: 'center',
  },
  pressed: { opacity: 0.68 },
  dots: {
    height: 8,
    marginTop: spacing.section,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.sm,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: radii.full,
    backgroundColor: colors.white,
  },
  dotActive: { backgroundColor: colors.accent },
});
