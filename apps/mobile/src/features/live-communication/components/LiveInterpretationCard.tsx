import {
  AudioLines,
  CircleAlert,
  Radio,
  RefreshCcw,
} from 'lucide-react-native';
import { Image, StyleSheet, View } from 'react-native';

import { RadarIndicator } from '@/components/silent-voice';
import { AppText, Button, Card } from '@/components/ui';
import { colors, fontFamilies, radii, spacing } from '@/theme';

import type { LiveSessionState } from '../types/live-session';
import { ConfidenceIndicator } from './ConfidenceIndicator';

const waveform = require('@/assets/images/live-communication/context-waveform.png');

type LiveInterpretationCardProps = {
  session: LiveSessionState;
  onRetry: () => void;
};

const phaseCopy = {
  ready: {
    title: 'Pronto para falar',
    description:
      'Pressione e mantenha o botão do Silent Voice para iniciar uma tentativa.',
  },
  capturing: {
    title: 'Captando intenção...',
    description: 'Solte o botão quando terminar.',
  },
  decoding: {
    title: 'Interpretando sinais...',
    description: 'Organizando os sinais captados com segurança.',
  },
} as const;

export function LiveInterpretationCard({
  session,
  onRetry,
}: LiveInterpretationCardProps) {
  const showConfidence =
    session.candidate !== undefined && session.confidence !== undefined;
  const semanticSuccess = session.phase === 'confirmed';

  return (
    <Card
      accessibilityLabel="Interpretação atual"
      style={[styles.card, semanticSuccess && styles.confirmedCard]}
    >
      {session.phase === 'idle' ? (
        <View style={styles.copyBlock}>
          <AppText style={styles.stateTitle} variant="sectionTitle">
            Pronto para iniciar
          </AppText>
          <AppText tone="secondary" variant="bodySmall">
            Inicie uma sessão para preparar o módulo.
          </AppText>
        </View>
      ) : null}

      {session.phase === 'ready' ||
      session.phase === 'capturing' ||
      session.phase === 'decoding' ? (
        <View style={styles.captureLayout}>
          <RadarIndicator
            accessibilityLabel={phaseCopy[session.phase].title}
            center="dot"
            rings={3}
            size={64}
          />
          <View style={styles.captureCopy}>
            <AppText style={styles.stateTitle} variant="sectionTitle">
              {phaseCopy[session.phase].title}
            </AppText>
            <AppText tone="secondary" variant="bodySmall">
              {phaseCopy[session.phase].description}
            </AppText>
          </View>
        </View>
      ) : null}

      {session.phase === 'candidate' ? (
        <CandidateContent label="Possível intenção" session={session} />
      ) : null}

      {session.phase === 'validating' ? (
        <CandidateContent label="Validando intenção..." session={session} />
      ) : null}

      {session.phase === 'confirmed' ? (
        <View style={styles.copyBlock}>
          <AppText
            style={styles.confirmedTitle}
            tone="accent"
            variant="sectionTitle"
          >
            Intenção confirmada
          </AppText>
          <CandidateText candidate={session.candidate} />
        </View>
      ) : null}

      {session.phase === 'speaking' ? (
        <View style={styles.copyBlock}>
          <View style={styles.inlineState}>
            <AudioLines color={colors.accent} size={18} />
            <AppText style={styles.stateTitle} variant="sectionTitle">
              Reproduzindo voz...
            </AppText>
          </View>
          <CandidateText candidate={session.candidate} />
          <View style={styles.audioFrame}>
            <Image
              resizeMode="cover"
              source={waveform}
              style={styles.audioWave}
            />
          </View>
        </View>
      ) : null}

      {session.phase === 'needsRetry' ? (
        <View style={styles.copyBlock}>
          <View style={styles.inlineState}>
            <RefreshCcw color={colors.accent} size={18} />
            <AppText style={styles.retryTitle} variant="cardTitle">
              Não foi possível confirmar sua intenção.
            </AppText>
          </View>
          <AppText tone="secondary" variant="bodySmall">
            Verifique o posicionamento do dispositivo e tente novamente.
          </AppText>
          <Button label="Tentar novamente" onPress={onRetry} variant="ghost" />
        </View>
      ) : null}

      {session.phase === 'error' ? (
        <View style={styles.copyBlock}>
          <View style={styles.inlineState}>
            <CircleAlert color={colors.error} size={18} />
            <AppText style={styles.retryTitle} variant="cardTitle">
              Sessão indisponível
            </AppText>
          </View>
          <AppText tone="secondary" variant="bodySmall">
            Ocorreu uma falha real no sistema. Encerre a sessão e tente
            novamente.
          </AppText>
        </View>
      ) : null}

      {showConfidence ? (
        <ConfidenceIndicator value={session.confidence ?? 0} />
      ) : null}
    </Card>
  );
}

function CandidateContent({
  label,
  session,
}: {
  label: string;
  session: LiveSessionState;
}) {
  return (
    <View style={styles.copyBlock}>
      <View style={styles.inlineState}>
        <Radio color={colors.accent} size={18} />
        <AppText
          style={styles.candidateLabel}
          tone={session.phase === 'validating' ? 'accent' : 'secondary'}
          variant="cardTitle"
        >
          {label}
        </AppText>
      </View>
      <CandidateText candidate={session.candidate} />
      {session.phase === 'candidate' ? (
        <AppText tone="secondary" variant="caption">
          A intenção ainda não foi confirmada.
        </AppText>
      ) : null}
    </View>
  );
}

function CandidateText({ candidate }: { candidate?: string }) {
  return <AppText style={styles.candidate}>“{candidate ?? ''}”</AppText>;
}

const styles = StyleSheet.create({
  card: { gap: spacing.lg, padding: spacing.md },
  confirmedCard: {
    borderWidth: 1,
    borderColor: colors.accent,
    backgroundColor: colors.accentSubtle,
  },
  copyBlock: { gap: spacing.sm },
  stateTitle: { fontSize: 16, lineHeight: 22 },
  confirmedTitle: { fontSize: 16, lineHeight: 22 },
  retryTitle: { minWidth: 0, flex: 1, fontSize: 13, lineHeight: 18 },
  captureLayout: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.lg,
  },
  captureCopy: { minWidth: 0, flex: 1, gap: spacing.sm },
  inlineState: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  candidateLabel: { fontSize: 12, lineHeight: 16 },
  candidate: {
    fontFamily: fontFamilies.bold,
    fontSize: 20,
    lineHeight: 28,
    color: colors.primary,
  },
  audioFrame: {
    height: 18,
    overflow: 'hidden',
    borderRadius: radii.control,
  },
  audioWave: { width: '100%', height: 18, opacity: 0.8 },
});
