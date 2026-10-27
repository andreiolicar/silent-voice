import {
  Activity,
  Cable,
  Camera,
  Check,
  CheckCircle2,
  CircleAlert,
  ScanLine,
} from 'lucide-react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { StyleSheet, View } from 'react-native';

import { ScreenHeading } from '@/components/layout';
import { StatusBadge } from '@/components/silent-voice';
import { AppText, Button, Card } from '@/components/ui';
import type {
  CalibrationCaptureState,
  CalibrationOrigin,
  CalibrationStep,
} from '@/domain/calibration';
import { colors, radii, spacing } from '@/theme';
import { MainAppScreen } from '@/features/system-overview/components/MainAppScreen';
import { SystemAppHeader } from '@/features/system-overview/components/SystemAppHeader';

import { CalibrationCapturePanel } from '../components/CalibrationCapturePanel';
import { CalibrationProgress } from '../components/CalibrationProgress';
import { CalibrationResultRow } from '../components/CalibrationResultRow';
import { CalibrationVisualPanel } from '../components/CalibrationVisualPanel';
import {
  resolveCalibrationInspection,
  resolveCalibrationOrigin,
} from '../data/calibration.mock';
import { useMockCalibrationFlow } from '../hooks/useMockCalibrationFlow';

const preparationItems = [
  { icon: Cable, label: 'Módulo Silent Voice conectado' },
  { icon: Activity, label: 'Sensor posicionado' },
  { icon: Camera, label: 'Câmera direcionada para sua boca' },
  { icon: CheckCircle2, label: 'Ambiente confortável' },
] as const;

export default function CalibrationScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{
    origin?: string | string[];
    state?: string | string[];
    step?: string | string[];
  }>();
  const origin = resolveCalibrationOrigin(params.origin);
  const inspection = resolveCalibrationInspection(params.step, params.state);
  const flow = useMockCalibrationFlow({
    inspectedState: inspection?.state,
    inspectedStep: inspection?.step,
  });

  const handleBack = () => {
    if (router.canGoBack()) router.back();
    else router.replace(origin === 'setup' ? '/connection' : '/hub');
  };

  const handleRetry = () => {
    flow.retryCurrentStep();
    if (inspection) {
      router.setParams({ state: undefined, step: undefined });
    }
  };

  const handleComplete = () => {
    router.replace(origin === 'setup' ? '/home' : '/hub');
  };

  return (
    <MainAppScreen contentStyle={styles.content} showBottomNavigation={false}>
      <SystemAppHeader onBack={handleBack} />

      <View style={styles.heading}>
        <ScreenHeading
          subtitle="Ensine o Silent Voice a reconhecer seus sinais."
          title="Calibração"
        />
      </View>

      <View style={styles.progress}>
        <CalibrationProgress step={flow.step} />
      </View>

      <View style={styles.stage}>
        <CalibrationStage
          captureState={flow.captureState}
          onAdvance={flow.advance}
          onComplete={handleComplete}
          onRetry={handleRetry}
          origin={origin}
          result={flow.result}
          step={flow.step}
        />
      </View>
    </MainAppScreen>
  );
}

type CalibrationStageProps = {
  captureState: ReturnType<typeof useMockCalibrationFlow>['captureState'];
  onAdvance: () => void;
  onComplete: () => void;
  onRetry: () => void;
  origin: CalibrationOrigin;
  result: ReturnType<typeof useMockCalibrationFlow>['result'];
  step: CalibrationStep;
};

function CalibrationStage({
  captureState,
  onAdvance,
  onComplete,
  onRetry,
  origin,
  result,
  step,
}: CalibrationStageProps) {
  if (step === 'preparation') {
    return <PreparationStage onAdvance={onAdvance} />;
  }

  if (step === 'rest') {
    return (
      <CaptureStageAction
        onAdvance={onAdvance}
        onRetry={onRetry}
        state={captureState}
      >
        <CalibrationCapturePanel
          description="Relaxe o rosto e permaneça sem tentar falar por alguns segundos."
          state={captureState}
          title="Fique em repouso"
          variant="rest"
        />
      </CaptureStageAction>
    );
  }

  if (step === 'muscle') {
    return (
      <CaptureStageAction
        onAdvance={onAdvance}
        onRetry={onRetry}
        state={captureState}
      >
        <CalibrationCapturePanel
          description="Pressione e mantenha o botão do Silent Voice enquanto faz o movimento de fala."
          state={captureState}
          title="Agora tente falar"
          variant="muscle"
        />
      </CaptureStageAction>
    );
  }

  if (step === 'visual') {
    return (
      <CaptureStageAction
        onAdvance={onAdvance}
        onRetry={onRetry}
        state={captureState}
      >
        <CalibrationVisualPanel state={captureState} />
      </CaptureStageAction>
    );
  }

  if (step === 'validation') {
    return (
      <Card style={styles.validationCard}>
        <View style={styles.stageCopy}>
          <AppText variant="sectionTitle">Validando calibração</AppText>
          <AppText tone="secondary" variant="bodySmall">
            Estamos conferindo se as leituras necessárias foram capturadas.
          </AppText>
        </View>

        <View style={styles.resultList}>
          <CalibrationResultRow label="Repouso" state={result.rest} />
          <CalibrationResultRow label="Sinal muscular" state={result.muscle} />
          <CalibrationResultRow
            label="Movimento da boca"
            state={result.visual}
          />
        </View>

        <StatusBadge
          icon={captureState === 'success' ? Check : ScanLine}
          label={
            captureState === 'success'
              ? 'Calibração concluída'
              : 'Validando leituras...'
          }
          size="compact"
          tone={captureState === 'success' ? 'success' : 'warning'}
        />
      </Card>
    );
  }

  return <CompletionStage onComplete={onComplete} origin={origin} />;
}

function PreparationStage({ onAdvance }: { onAdvance: () => void }) {
  return (
    <View style={styles.stageStack}>
      <Card style={styles.preparationCard}>
        <View style={styles.stageCopy}>
          <AppText variant="sectionTitle">
            Vamos calibrar seu Silent Voice
          </AppText>
          <AppText tone="secondary" variant="bodySmall">
            Esse processo ajuda o sistema a reconhecer seus sinais com mais
            precisão.
          </AppText>
        </View>

        <View style={styles.checklist}>
          {preparationItems.map(({ icon: Icon, label }) => (
            <View
              accessibilityLabel={`${label}: pronto`}
              key={label}
              style={styles.checklistItem}
            >
              <View style={styles.checkIcon}>
                <Icon color={colors.accent} size={18} strokeWidth={1.8} />
              </View>
              <AppText style={styles.checklistLabel} variant="bodySmall">
                {label}
              </AppText>
              <Check color={colors.accent} size={18} strokeWidth={2.5} />
            </View>
          ))}
        </View>
      </Card>

      <View
        accessibilityLabel="Interrompa o processo se sentir qualquer desconforto."
        accessible
        style={styles.safetyNotice}
      >
        <CircleAlert color={colors.warning} size={18} />
        <AppText style={styles.safetyCopy} tone="secondary" variant="caption">
          Interrompa o processo se sentir qualquer desconforto.
        </AppText>
      </View>

      <Button label="Começar calibração" onPress={onAdvance} />
    </View>
  );
}

type CaptureStageActionProps = {
  children: React.ReactNode;
  onAdvance: () => void;
  onRetry: () => void;
  state: CalibrationCaptureState;
};

function CaptureStageAction({
  children,
  onAdvance,
  onRetry,
  state,
}: CaptureStageActionProps) {
  return (
    <View style={styles.stageStack}>
      {children}
      {state === 'retry' ? (
        <Button label="Tentar novamente" onPress={onRetry} />
      ) : null}
      {state === 'success' ? (
        <Button label="Continuar" onPress={onAdvance} />
      ) : null}
    </View>
  );
}

function CompletionStage({
  onComplete,
  origin,
}: {
  onComplete: () => void;
  origin: CalibrationOrigin;
}) {
  const actionLabel = origin === 'setup' ? 'Ir para início' : 'Voltar ao Hub';

  return (
    <View style={styles.stageStack}>
      <Card style={styles.completionCard}>
        <View style={styles.completeIcon}>
          <Check color={colors.white} size={30} strokeWidth={2.5} />
        </View>
        <View style={styles.completionCopy}>
          <AppText variant="sectionTitle">Tudo pronto</AppText>
          <AppText style={styles.completeLead} variant="body">
            Seu Silent Voice está calibrado para começar.
          </AppText>
          <AppText tone="secondary" variant="bodySmall">
            Você pode refazer a calibração quando precisar.
          </AppText>
        </View>
      </Card>
      <Button label={actionLabel} onPress={onComplete} />
    </View>
  );
}

const styles = StyleSheet.create({
  content: { paddingBottom: spacing.xl },
  heading: { marginTop: spacing.section },
  progress: { marginTop: spacing.lgPlus },
  stage: { marginTop: spacing.xl },
  stageStack: { gap: spacing.lg },
  stageCopy: { gap: spacing.sm },
  preparationCard: { gap: spacing.xl, padding: spacing.lg },
  checklist: { gap: spacing.md },
  checklistItem: {
    minHeight: 38,
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.smPlus,
  },
  checklistLabel: { minWidth: 0, flex: 1 },
  checkIcon: {
    width: 36,
    height: 36,
    flexShrink: 0,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: radii.full,
    backgroundColor: colors.accentSoft,
  },
  safetyNotice: {
    minHeight: 48,
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderRadius: radii.control,
    backgroundColor: colors.warningSoft,
  },
  safetyCopy: { minWidth: 0, flex: 1 },
  validationCard: { gap: spacing.lg, padding: spacing.lg },
  resultList: { gap: spacing.sm },
  completionCard: {
    alignItems: 'center',
    gap: spacing.lg,
    padding: spacing.xl,
  },
  completeIcon: {
    width: 64,
    height: 64,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: radii.full,
    backgroundColor: colors.accent,
  },
  completionCopy: { alignItems: 'center', gap: spacing.sm },
  completeLead: { textAlign: 'center' },
});
