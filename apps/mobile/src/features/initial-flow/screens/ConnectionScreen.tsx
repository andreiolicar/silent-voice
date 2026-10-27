import { Cable, Link, RefreshCcw, Usb } from 'lucide-react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useMemo, useState } from 'react';
import { Platform, StyleSheet, View } from 'react-native';

import {
  DeviceCard,
  PrivacyNotice,
  StatusBadge,
} from '@/components/silent-voice';
import { AppText, Button, Card } from '@/components/ui';
import type { DeviceConnectionState } from '@/domain/device';
import {
  BrandLogo,
  InitialFlowScreen,
} from '@/features/initial-flow/components';
import { colors, fontFamilies, radii } from '@/theme';

import {
  connectionStateCopy,
  mockUsbConnectionSequence,
  resolveMockConnectionState,
} from '../data/connection.mock';

const POST_CONNECTION_ROUTE = '/calibration?origin=setup' as const;
const MOCK_STEP_DURATION = 850;

export default function Connection() {
  const router = useRouter();
  const params = useLocalSearchParams<{ state?: string | string[] }>();
  const inspectedState = resolveMockConnectionState(params.state);
  const [flowVersion, setFlowVersion] = useState(0);
  const [mockState, setMockState] =
    useState<DeviceConnectionState>('waitingForUsb');
  const state = inspectedState ?? mockState;

  useEffect(() => {
    if (inspectedState) return;

    const timers = mockUsbConnectionSequence
      .slice(1)
      .map((nextState, index) =>
        setTimeout(
          () => setMockState(nextState),
          MOCK_STEP_DURATION * (index + 1),
        ),
      );
    const navigationTimer = setTimeout(
      () => router.replace(POST_CONNECTION_ROUTE),
      MOCK_STEP_DURATION * mockUsbConnectionSequence.length,
    );

    return () => {
      timers.forEach(clearTimeout);
      clearTimeout(navigationTimer);
    };
  }, [flowVersion, inspectedState, router]);

  const copy = connectionStateCopy[state];
  const isConnected = state === 'connected';
  const isFailed = state === 'failed';
  const action = useMemo(() => {
    if (isConnected) {
      return {
        icon: Link,
        label: 'Continuar',
        onPress: () => router.replace(POST_CONNECTION_ROUTE),
      };
    }
    if (isFailed) {
      return {
        icon: RefreshCcw,
        label: 'Tentar novamente',
        onPress: () => {
          if (inspectedState) router.replace('/connection');
          else {
            setMockState('waitingForUsb');
            setFlowVersion((current) => current + 1);
          }
        },
      };
    }
    return null;
  }, [inspectedState, isConnected, isFailed, router]);

  return (
    <InitialFlowScreen background={null} contentStyle={styles.content}>
      <BrandLogo style={styles.logo} />

      <View style={styles.header}>
        <View style={styles.headingCopy}>
          <AppText style={styles.title} variant="screenTitle">
            Conectar{`\n`}dispositivo
          </AppText>
          <AppText style={styles.subtitle} tone="secondary">
            Conecte o Silent Voice ao celular{`\n`}usando o cabo de dados USB.
          </AppText>
        </View>
        <View style={styles.headerIcon}>
          <Cable color={colors.accent} size={46} strokeWidth={1.4} />
        </View>
      </View>

      <Card style={styles.statusCard}>
        <View style={styles.statusIcon}>
          <Usb
            color={copy.tone === 'error' ? colors.error : colors.accent}
            size={24}
          />
        </View>
        <View style={styles.statusCopy}>
          <AppText style={styles.statusTitle}>{copy.title}</AppText>
          <AppText style={styles.statusDescription} tone="secondary">
            {copy.description}
          </AppText>
        </View>
        <StatusBadge label="USB" size="compact" tone={copy.tone} />
      </Card>

      <View style={styles.deviceSection}>
        <AppText style={styles.sectionLabel} tone="secondary">
          MÓDULO SILENT VOICE
        </AppText>
        <DeviceCard
          description="Raspberry Pi Zero 2 W"
          icon={Usb}
          name="Módulo Silent Voice"
          status={copy.moduleStatus}
          statusTone={copy.tone}
        />
      </View>

      <View style={styles.spacer} />
      <View style={styles.footer}>
        {action ? (
          <Button
            contentStyle={styles.buttonContent}
            label={action.label}
            leftIcon={action.icon}
            onPress={action.onPress}
            style={styles.button}
          />
        ) : (
          <Button
            contentStyle={styles.buttonContent}
            disabled
            label={copy.title}
            leftIcon={Usb}
            loading={state === 'connecting'}
            style={styles.button}
          />
        )}
        <PrivacyNotice
          compact
          text="A conexão USB será autorizada quando o módulo estiver conectado."
        />
      </View>
    </InitialFlowScreen>
  );
}

const styles = StyleSheet.create({
  content: {
    paddingTop: Platform.select({ web: 75, default: 18 }),
    paddingBottom: 30,
  },
  logo: { alignSelf: 'center', marginBottom: 35 },
  header: {
    minHeight: 112,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  headingCopy: { gap: 10 },
  title: { fontSize: 26, lineHeight: 28, letterSpacing: -0.4 },
  subtitle: {
    fontFamily: fontFamilies.regular,
    fontSize: 12,
    lineHeight: 16,
  },
  headerIcon: {
    width: 96,
    height: 96,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: radii.full,
    backgroundColor: colors.accentSoft,
  },
  statusCard: {
    minHeight: 80,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginTop: 35,
    padding: 12,
  },
  statusIcon: {
    width: 44,
    height: 44,
    flexShrink: 0,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: radii.full,
    backgroundColor: colors.background,
  },
  statusCopy: { minWidth: 0, flex: 1, gap: 5 },
  statusTitle: {
    fontFamily: fontFamilies.semiBold,
    fontSize: 12,
    lineHeight: 15,
  },
  statusDescription: {
    fontFamily: fontFamilies.medium,
    fontSize: 9,
    lineHeight: 12,
  },
  deviceSection: { gap: 12, marginTop: 26 },
  sectionLabel: {
    fontFamily: fontFamilies.medium,
    fontSize: 8,
    lineHeight: 10,
    letterSpacing: 1,
  },
  spacer: { flexGrow: 1, minHeight: 20 },
  footer: { gap: 12 },
  button: { minHeight: 42, height: 42 },
  buttonContent: { gap: 10 },
});
