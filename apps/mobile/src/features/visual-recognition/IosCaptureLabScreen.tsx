import { useFocusEffect, useRouter } from 'expo-router';
import { useCallback, useEffect, useRef, useState } from 'react';
import { AppState, StyleSheet, View } from 'react-native';
import { Screen, ScreenHeading } from '@/components/layout';
import { AppText, Button, Card } from '@/components/ui';
import { colors, radii, spacing } from '@/theme';
import { useAuth } from '@/features/auth/AuthProvider';
import { labReturnDestination } from './lab-navigation';
import {
  summarizeCapture,
  verifySyntheticCapture,
  verifySyntheticNormalization,
  type CameraPermission,
} from './capture-diagnostics';
import {
  CapturePreview,
  nativeCapture,
  type CaptureViewHandle,
} from './native-capture';

type Operation =
  | 'capture'
  | 'capture-normalized'
  | 'permission'
  | 'synthetic'
  | 'normalization-synthetic'
  | null;

export default function IosCaptureLabScreen() {
  const router = useRouter();
  const { session, onboarding } = useAuth();
  const preview = useRef<CaptureViewHandle | null>(null);
  const focused = useRef(false);
  const operation = useRef<Operation>(null);
  const generation = useRef(0);
  const [busy, setBusy] = useState<Operation>(null);
  const [permission, setPermission] =
    useState<CameraPermission>('undetermined');
  const [message, setMessage] = useState('Pronto para os ensaios locais.');
  const [synthetic, setSynthetic] = useState<boolean | null>(null);
  const [bgrSynthetic, setBgrSynthetic] = useState<boolean | null>(null);
  const [summary, setSummary] = useState<ReturnType<
    typeof summarizeCapture
  > | null>(null);

  const cancel = useCallback(() => {
    generation.current++;
    operation.current = null;
    setBusy(null);
    setSummary(null);
    setMessage('Captura cancelada.');
    void preview.current?.cancel().catch(() => {});
  }, []);

  useFocusEffect(
    useCallback(() => {
      focused.current = true;
      operation.current = null;
      setBusy(null);
      void nativeCapture
        ?.getPermission()
        .then((value) => {
          if (focused.current) setPermission(value);
        })
        .catch(() => {
          if (focused.current)
            setMessage('Não foi possível consultar a câmera.');
        });
      return () => {
        focused.current = false;
        generation.current++;
        operation.current = null;
        void preview.current?.cancel().catch(() => {});
      };
    }, []),
  );

  useEffect(() => {
    const listener = AppState.addEventListener('change', (state) => {
      if (
        state !== 'active' &&
        (operation.current === 'capture' ||
          operation.current === 'capture-normalized')
      )
        cancel();
      if (state === 'active') {
        void nativeCapture
          ?.getPermission()
          .then((value) => {
            if (focused.current) setPermission(value);
          })
          .catch(() => {});
      }
    });
    return () => listener.remove();
  }, [cancel]);

  const run = async (kind: Exclude<Operation, null>) => {
    if (!nativeCapture || operation.current || !focused.current) return;
    const current = ++generation.current;
    operation.current = kind;
    setBusy(kind);
    const active = () => focused.current && current === generation.current;
    try {
      if (kind === 'permission') {
        const next = await nativeCapture.requestPermission();
        if (active()) {
          setPermission(next);
          setMessage(
            next === 'granted'
              ? 'Câmera autorizada.'
              : 'A captura requer autorização da câmera nos Ajustes.',
          );
        }
      } else if (kind === 'synthetic') {
        const result = verifySyntheticCapture(
          await nativeCapture.syntheticFrames(),
        );
        console.info(
          'SilentVoiceLab synthetic',
          result.passed ? 'PASS' : 'FAIL',
        );
        if (active()) {
          setSynthetic(result.passed);
          setMessage(
            result.passed
              ? 'Teste sintético aprovado: Swift → Hermes, 121 frames.'
              : 'O teste sintético encontrou uma divergência.',
          );
        }
      } else if (kind === 'normalization-synthetic') {
        const passed = verifySyntheticNormalization(
          await nativeCapture.syntheticNormalization(),
        );
        if (active()) {
          setBgrSynthetic(passed);
          setMessage(
            passed
              ? 'Conversão sintética BGR8: PASS, referência Python exata.'
              : 'Conversão sintética BGR8: FAIL.',
          );
        }
      } else {
        if (!preview.current || permission !== 'granted') return;
        setSummary(null);
        setMessage('Capturando por quatro segundos…');
        const report =
          kind === 'capture-normalized'
            ? await preview.current.captureNormalized()
            : await preview.current.capture();
        const result = summarizeCapture(report);
        console.info(
          'SilentVoiceLab capture',
          JSON.stringify({
            status: result.status,
            frameCount: result.frameCount,
            durationSeconds: result.durationSeconds,
            fps: result.fps,
            readFailures: result.readFailures,
            dimensions: result.dimensions,
            pixelFormat: result.pixelFormat,
            orientation: result.orientation,
            mirrored: result.mirrored,
            contractStatus: result.contract.status,
          }),
        );
        if (active()) {
          setSummary(result);
          setMessage(
            report.status === 'complete'
              ? 'Aquisição da câmera concluída.'
              : report.status === 'cancelled'
                ? 'Captura cancelada.'
                : report.error === 'camera-orientation'
                  ? 'Gire o iPhone para a horizontal e mantenha-o firme antes de capturar BGR8.'
                  : 'Não foi possível concluir a captura.',
          );
        }
      }
    } catch {
      if (active())
        setMessage('O módulo nativo não concluiu o ensaio. Tente novamente.');
    } finally {
      if (active()) {
        operation.current = null;
        setBusy(null);
      }
    }
  };

  const available = Boolean(nativeCapture && CapturePreview);
  return (
    <Screen scroll contentStyle={styles.screen}>
      <ScreenHeading
        title="Ensaio no iPhone"
        subtitle="Captura frontal · build privada"
      />
      <Card>
        <AppText variant="cardTitle">Reconhecimento indisponível</AppText>
        <AppText tone="secondary">
          Este ensaio mede aquisição e timestamps. Nenhuma imagem é salva ou
          enviada.
        </AppText>
      </Card>
      <AppText accessibilityLiveRegion="polite">
        {available ? message : 'Módulo de captura indisponível nesta build.'}
      </AppText>
      <Button
        label="Executar teste sintético"
        disabled={!available || Boolean(busy)}
        onPress={() => void run('synthetic')}
      />
      {synthetic !== null ? (
        <AppText>Teste sintético: {synthetic ? 'PASS' : 'FAIL'}</AppText>
      ) : null}
      <Button
        label="Testar conversão BGR8 sintética"
        disabled={!available || Boolean(busy)}
        onPress={() => void run('normalization-synthetic')}
      />
      {bgrSynthetic !== null ? (
        <AppText>
          Conversão BGR8 sintética: {bgrSynthetic ? 'PASS' : 'FAIL'}
        </AppText>
      ) : null}
      <Button
        label="Autorizar câmera"
        variant="ghost"
        disabled={!available || Boolean(busy) || permission === 'granted'}
        onPress={() => void run('permission')}
      />
      <AppText tone="secondary">Permissão: {permission}</AppText>
      {CapturePreview ? (
        <CapturePreview
          ref={preview}
          style={styles.preview}
          accessibilityLabel="Prévia da câmera frontal durante a captura"
        />
      ) : (
        <View style={styles.preview} />
      )}
      <Button
        label={busy === 'capture' ? 'Capturando…' : 'Capturar quatro segundos'}
        disabled={!available || Boolean(busy) || permission !== 'granted'}
        onPress={() => void run('capture')}
      />
      <AppText tone="secondary">
        Para o ensaio BGR8, segure o iPhone na horizontal. A interface continua
        em retrato.
      </AppText>
      <Button
        label={
          busy === 'capture-normalized'
            ? 'Cancelar captura BGR8'
            : 'Capturar BGR8 horizontal · quatro segundos'
        }
        variant={busy === 'capture-normalized' ? 'danger' : 'primary'}
        disabled={
          !available ||
          (Boolean(busy) && busy !== 'capture-normalized') ||
          permission !== 'granted'
        }
        onPress={() =>
          busy === 'capture-normalized'
            ? cancel()
            : void run('capture-normalized')
        }
      />
      {busy === 'capture' ? (
        <Button label="Cancelar captura" variant="danger" onPress={cancel} />
      ) : null}
      {summary ? (
        <Card>
          <AppText variant="cardTitle">Resultado da aquisição</AppText>
          <AppText>
            Frames: {summary.frameCount} · perdas: {summary.readFailures}
          </AppText>
          <AppText>
            Duração: {summary.durationSeconds?.toFixed(3) ?? '—'} s · FPS:{' '}
            {summary.fps?.toFixed(2) ?? '—'}
          </AppText>
          <AppText>
            Origem: {summary.sourceDimensions} · {summary.sourcePixelFormat}
          </AppText>
          {summary.sourceByteCount !== null ? (
            <AppText>
              Bytes de origem: {summary.sourceByteCount} · stride:{' '}
              {summary.sourceBytesPerRow}
            </AppText>
          ) : null}
          {summary.normalizationStatus === 'complete' ? (
            <AppText>
              Convertido: {summary.dimensions} · {summary.pixelFormat} ·{' '}
              {summary.byteCountPerFrame} bytes/frame
            </AppText>
          ) : null}
          <AppText>
            Orientação: {summary.orientation} · espelhado:{' '}
            {String(summary.mirrored)}
          </AppText>
          <AppText>
            Gate técnico:{' '}
            {summary.contract.status === 'pass' ? 'PASS' : 'BLOCKED'}
          </AppText>
          <AppText tone="secondary">
            {summary.normalizationStatus === 'complete'
              ? 'Conversão concluída. Reconhecimento indisponível.'
              : 'Conversão BGR8 não concluída neste ensaio. Reconhecimento indisponível.'}
          </AppText>
          {summary.error ? (
            <AppText tone="error">Erro: {summary.error}</AppText>
          ) : null}
        </Card>
      ) : null}
      <Button
        label="Voltar ao aplicativo"
        variant="ghost"
        onPress={() => {
          cancel();
          router.replace(labReturnDestination(Boolean(session), onboarding));
        }}
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  screen: { gap: spacing.lg },
  preview: {
    height: 240,
    backgroundColor: colors.primary,
    borderRadius: radii.card,
    overflow: 'hidden',
  },
});
