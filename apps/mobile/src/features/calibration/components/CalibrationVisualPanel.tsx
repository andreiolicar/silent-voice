import {
  Camera,
  Check,
  Focus,
  RotateCcw,
  type LucideIcon,
} from 'lucide-react-native';
import { StyleSheet, View } from 'react-native';

import { StatusBadge } from '@/components/silent-voice';
import { AppText, Card } from '@/components/ui';
import type { CalibrationCaptureState } from '@/domain/calibration';
import { colors, radii, spacing } from '@/theme';

type CalibrationVisualPanelProps = {
  state: CalibrationCaptureState;
};

type VisualPresentation = {
  icon: LucideIcon;
  label: string;
  tone: 'error' | 'neutral' | 'success' | 'warning';
};

export function CalibrationVisualPanel({ state }: CalibrationVisualPanelProps) {
  const presentation = getVisualPresentation(state);

  return (
    <Card
      accessibilityLabel={`Câmera do módulo. ${presentation.label}`}
      style={styles.card}
    >
      <View style={styles.copy}>
        <AppText variant="sectionTitle">Movimento da boca</AppText>
        <AppText tone="secondary" variant="bodySmall">
          Olhe para frente e repita o movimento de fala quando solicitado.
        </AppText>
      </View>

      <View accessibilityLabel="Área de enquadramento da câmera do módulo">
        <View style={styles.frame}>
          <View style={styles.guide}>
            <Focus color={colors.accent} size={48} strokeWidth={1.3} />
            <View style={styles.cameraBadge}>
              <Camera color={colors.primary} size={18} strokeWidth={1.8} />
            </View>
          </View>
        </View>
      </View>

      <StatusBadge
        icon={presentation.icon}
        label={presentation.label}
        size="compact"
        tone={presentation.tone}
      />
      {state === 'retry' ? (
        <AppText tone="secondary" variant="bodySmall">
          Não conseguimos obter uma leitura estável.
        </AppText>
      ) : null}
    </Card>
  );
}

function getVisualPresentation(
  state: CalibrationCaptureState,
): VisualPresentation {
  if (state === 'success') {
    return { icon: Check, label: 'Boa visibilidade', tone: 'success' };
  }
  if (state === 'retry') {
    return { icon: RotateCcw, label: 'Reposicione o módulo', tone: 'error' };
  }
  if (state === 'processing' || state === 'capturing') {
    return {
      icon: Focus,
      label: 'Ajustando enquadramento',
      tone: 'warning',
    };
  }
  return { icon: Camera, label: 'Prepare o enquadramento', tone: 'neutral' };
}

const styles = StyleSheet.create({
  card: { gap: spacing.lg, padding: spacing.lg },
  copy: { gap: spacing.xs },
  frame: {
    height: 156,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: colors.borderStrong,
    borderRadius: radii.card,
    backgroundColor: colors.background,
  },
  guide: {
    width: 112,
    height: 80,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: colors.accent,
    borderRadius: radii.card,
    backgroundColor: colors.accentSubtle,
  },
  cameraBadge: {
    marginTop: spacing.xs,
    padding: spacing.xs,
    borderRadius: radii.full,
    backgroundColor: colors.surface,
  },
});
