import { AudioLines, CircleAlert, CircleDot, Radio } from 'lucide-react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useMemo, useState } from 'react';
import { StyleSheet, View } from 'react-native';

import { ScreenHeading } from '@/components/layout';
import { PrivacyNotice, StatusBadge } from '@/components/silent-voice';
import { Button } from '@/components/ui';
import { spacing } from '@/theme';

import { ContextWindowCard } from '../components/ContextWindowCard';
import { LiveInterpretationCard } from '../components/LiveInterpretationCard';
import { SessionHistoryCard } from '../components/SessionHistoryCard';
import {
  createMockLiveSessionState,
  resolveLiveSessionPhase,
} from '../data/live-session.mock';
import type { LiveSessionPhase } from '../types/live-session';
import { MainAppScreen } from '@/features/system-overview/components/MainAppScreen';
import { SystemAppHeader } from '@/features/system-overview/components/SystemAppHeader';

export default function LiveCommunicationScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ phase?: string | string[] }>();
  const requestedPhase = resolveLiveSessionPhase(params.phase);
  const [phase, setPhase] = useState<LiveSessionPhase>(
    () => requestedPhase ?? 'ready',
  );

  const session = useMemo(() => createMockLiveSessionState(phase), [phase]);
  const isSessionActive = phase !== 'idle';
  const sessionStatus = getSessionStatus(phase);

  const handleBack = () => {
    if (router.canGoBack()) router.back();
    else router.replace('/home');
  };

  return (
    <MainAppScreen activeItem="communication" contentStyle={styles.content}>
      <SystemAppHeader onBack={handleBack} />

      <View style={styles.heading}>
        <ScreenHeading
          subtitle="Interpretação em tempo real da sua intenção."
          title="Comunicação ao vivo"
        />
      </View>

      <View style={styles.section}>
        <View style={styles.statusRow}>
          <StatusBadge
            icon={sessionStatus.icon}
            label={sessionStatus.label}
            size="compact"
            tone={sessionStatus.tone}
          />
          <StatusBadge
            icon={phase === 'error' ? CircleAlert : undefined}
            label={phase === 'error' ? 'Falha do sistema' : 'Sistema estável'}
            size="compact"
            tone={phase === 'error' ? 'error' : 'success'}
          />
        </View>

        <LiveInterpretationCard
          onRetry={() => setPhase('ready')}
          session={session}
        />

        <ContextWindowCard entries={session.contextWindow} />

        <SessionHistoryCard entries={session.recentConfirmed} />

        <PrivacyNotice
          compact
          text="Seus dados são protegidos e não são compartilhados."
        />

        <Button
          label={isSessionActive ? 'Parar comunicação' : 'Iniciar comunicação'}
          onPress={() => setPhase(isSessionActive ? 'idle' : 'ready')}
          variant={isSessionActive ? 'danger' : 'primary'}
        />
      </View>
    </MainAppScreen>
  );
}

function getSessionStatus(phase: LiveSessionPhase) {
  if (phase === 'idle') {
    return { icon: Radio, label: 'Sessão parada', tone: 'neutral' as const };
  }

  if (phase === 'ready') {
    return {
      icon: CircleDot,
      label: 'Aguardando botão',
      tone: 'success' as const,
    };
  }

  if (phase === 'capturing') {
    return {
      icon: AudioLines,
      label: 'Captando agora',
      tone: 'success' as const,
    };
  }

  if (phase === 'confirmed' || phase === 'speaking') {
    return { icon: Radio, label: 'Sessão ativa', tone: 'success' as const };
  }

  if (phase === 'error') {
    return {
      icon: CircleAlert,
      label: 'Sessão interrompida',
      tone: 'error' as const,
    };
  }

  return {
    icon: Radio,
    label: 'Sessão ativa',
    tone: 'success' as const,
  };
}

const styles = StyleSheet.create({
  content: { paddingBottom: spacing.lgPlus },
  heading: { marginTop: spacing.section },
  section: { gap: spacing.md, marginTop: spacing.section },
  statusRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing.md,
  },
});
