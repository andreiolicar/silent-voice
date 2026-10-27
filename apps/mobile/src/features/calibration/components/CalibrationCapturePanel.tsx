import {
  AudioLines,
  Check,
  CircleDot,
  LoaderCircle,
  RotateCcw,
  type LucideIcon,
} from 'lucide-react-native';
import { StyleSheet, View } from 'react-native';

import { StatusBadge } from '@/components/silent-voice';
import { AppText, Card } from '@/components/ui';
import type { CalibrationCaptureState } from '@/domain/calibration';
import { colors, radii, spacing } from '@/theme';

import { calibrationStateProgress } from '../data/calibration.mock';

type CalibrationCapturePanelProps = {
  description: string;
  state: CalibrationCaptureState;
  title: string;
  variant: 'muscle' | 'rest';
};

type CapturePresentation = {
  icon: LucideIcon;
  label: string;
  tone: 'error' | 'neutral' | 'success' | 'warning';
};

export function CalibrationCapturePanel({
  description,
  state,
  title,
  variant,
}: CalibrationCapturePanelProps) {
  const presentation = getCapturePresentation(variant, state);
  const Icon = presentation.icon;
  const progress = calibrationStateProgress[state];

  return (
    <Card
      accessibilityLabel={`${title}. ${presentation.label}`}
      style={styles.card}
    >
      <View style={styles.headingRow}>
        <View style={styles.iconFrame}>
          <Icon color={colors.accent} size={26} strokeWidth={1.8} />
        </View>
        <View style={styles.headingCopy}>
          <AppText variant="sectionTitle">{title}</AppText>
          <AppText tone="secondary" variant="bodySmall">
            {description}
          </AppText>
        </View>
      </View>

      <View style={styles.statusArea}>
        <StatusBadge
          icon={presentation.icon}
          label={presentation.label}
          size="compact"
          tone={presentation.tone}
        />
        <View
          accessibilityLabel={`Progresso da etapa: ${Math.round(progress * 100)}%`}
          accessibilityRole="progressbar"
          accessibilityValue={{ max: 100, min: 0, now: progress * 100 }}
          style={styles.track}
        >
          <View
            style={[
              styles.fill,
              state === 'retry' && styles.retryFill,
              { width: `${progress * 100}%` },
            ]}
          />
        </View>
      </View>
    </Card>
  );
}

function getCapturePresentation(
  variant: CalibrationCapturePanelProps['variant'],
  state: CalibrationCaptureState,
): CapturePresentation {
  if (state === 'retry') {
    return {
      icon: RotateCcw,
      label: 'Não conseguimos obter uma leitura estável.',
      tone: 'error',
    };
  }

  if (variant === 'rest') {
    const restPresentation: Record<
      CalibrationCaptureState,
      CapturePresentation
    > = {
      idle: { icon: CircleDot, label: 'Pronto para começar', tone: 'neutral' },
      waiting: { icon: CircleDot, label: 'Aguardando', tone: 'neutral' },
      capturing: {
        icon: AudioLines,
        label: 'Captando referência...',
        tone: 'success',
      },
      processing: {
        icon: LoaderCircle,
        label: 'Organizando leitura...',
        tone: 'warning',
      },
      success: {
        icon: Check,
        label: 'Referência capturada',
        tone: 'success',
      },
      retry: { icon: RotateCcw, label: '', tone: 'error' },
    };
    return restPresentation[state];
  }

  const musclePresentation: Record<
    CalibrationCaptureState,
    CapturePresentation
  > = {
    idle: { icon: CircleDot, label: 'Prepare-se', tone: 'neutral' },
    waiting: {
      icon: CircleDot,
      label: 'Aguardando o botão físico',
      tone: 'neutral',
    },
    capturing: {
      icon: AudioLines,
      label: 'Captando seu sinal...',
      tone: 'success',
    },
    processing: {
      icon: LoaderCircle,
      label: 'Analisando leitura...',
      tone: 'warning',
    },
    success: {
      icon: Check,
      label: 'Sinal reconhecido',
      tone: 'success',
    },
    retry: { icon: RotateCcw, label: '', tone: 'error' },
  };
  return musclePresentation[state];
}

const styles = StyleSheet.create({
  card: { gap: spacing.xl, padding: spacing.lg },
  headingRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.md },
  iconFrame: {
    width: 52,
    height: 52,
    flexShrink: 0,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: radii.full,
    backgroundColor: colors.accentSoft,
  },
  headingCopy: { minWidth: 0, flex: 1, gap: spacing.xs },
  statusArea: { gap: spacing.md },
  track: {
    width: '100%',
    height: 6,
    overflow: 'hidden',
    borderRadius: radii.full,
    backgroundColor: colors.border,
  },
  fill: {
    height: '100%',
    borderRadius: radii.full,
    backgroundColor: colors.accent,
  },
  retryFill: { backgroundColor: colors.error },
});
