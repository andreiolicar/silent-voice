import {
  Cable,
  CircleCheck,
  Clock3,
  Cpu,
  Zap,
  type LucideIcon,
} from 'lucide-react-native';
import { useRouter } from 'expo-router';
import { useState } from 'react';
import { Image, Pressable, StyleSheet, View } from 'react-native';

import { MetricCard, RadarIndicator } from '@/components/silent-voice';
import { AppText, Card } from '@/components/ui';
import {
  colors,
  focusRing,
  fontFamilies,
  isFocusVisible,
  radii,
  spacing,
  webNoOutline,
} from '@/theme';

import { LiveCommunicationButton } from '../components/LiveCommunicationButton';
import { MainAppScreen } from '../components/MainAppScreen';
import { SystemAppHeader } from '../components/SystemAppHeader';
import {
  homeOverviewMock,
  type SystemMetricId,
} from '../data/system-overview.mock';

const headerWaves = require('@/assets/images/system-overview/home-header-waves.png');
const wearableAndPhone = require('@/assets/images/system-overview/wearable-and-phone.png');
const cardWaves = require('@/assets/images/system-overview/home-card-waves.png');

const metricIcons: Record<SystemMetricId, LucideIcon> = {
  power: Zap,
  latency: Clock3,
  connection: Cable,
  modules: Cpu,
};

export default function HomeScreen() {
  const router = useRouter();
  const [statusFocused, setStatusFocused] = useState(false);

  return (
    <MainAppScreen contentStyle={styles.content}>
      <SystemAppHeader />

      <View style={styles.greeting}>
        <View style={styles.greetingCopy}>
          <AppText style={styles.title}>
            Olá, {homeOverviewMock.user.name}
          </AppText>
          <AppText style={styles.subtitle} tone="secondary">
            {homeOverviewMock.user.welcome}
          </AppText>
        </View>
        <View style={styles.headerWavesFrame}>
          <Image source={headerWaves} style={styles.headerWaves} />
        </View>
      </View>

      <View style={styles.overviewSection}>
        <Pressable
          accessibilityLabel="Abrir saúde do sistema"
          accessibilityRole="button"
          onBlur={() => setStatusFocused(false)}
          onFocus={(event) => setStatusFocused(isFocusVisible(event))}
          onPress={() => router.push('/system-health')}
          style={({ pressed }) => [
            styles.cardPressable,
            webNoOutline,
            statusFocused && focusRing,
            pressed && styles.pressed,
          ]}
        >
          <Card style={styles.statusCard}>
            <View style={styles.statusLeft}>
              <View style={styles.statusIcon}>
                <CircleCheck color={colors.accent} size={28} />
              </View>
              <View style={styles.statusCopy}>
                <AppText style={styles.cardTitle}>
                  {homeOverviewMock.status.title}
                </AppText>
                <AppText style={styles.cardDescription} tone="secondary">
                  {homeOverviewMock.status.description}
                </AppText>
              </View>
            </View>
            <RadarIndicator
              accessibilityLabel="Sistema operacional"
              center="dot"
              rings={3}
              size={55}
            />
          </Card>
        </Pressable>

        <View style={styles.metrics}>
          {homeOverviewMock.metrics.map((metric) => (
            <MetricCard
              description={metric.description}
              icon={metricIcons[metric.id]}
              key={metric.id}
              label={metric.label}
              onPress={
                metric.id === 'modules'
                  ? () => router.push('/modules')
                  : undefined
              }
              style={styles.metricCard}
              value={metric.value}
            />
          ))}
        </View>

        <Card style={styles.communicationCard}>
          <View style={styles.communicationVisual}>
            <View style={styles.communicationRings}>
              <RadarIndicator
                accessibilityLabel="Comunicação disponível"
                center="none"
                rings={4}
                size={70}
              />
            </View>
            <View style={styles.wearableFrame}>
              <Image source={wearableAndPhone} style={styles.wearableImage} />
            </View>
          </View>
          <View style={styles.communicationRight}>
            <View style={styles.communicationCopy}>
              <AppText style={styles.cardTitle}>
                {homeOverviewMock.communication.title}
                <AppText style={styles.cardTitle} tone="accent">
                  .
                </AppText>
              </AppText>
              <AppText style={styles.cardDescription} tone="secondary">
                {homeOverviewMock.communication.description}
              </AppText>
            </View>
            <Image source={cardWaves} style={styles.cardWaves} />
          </View>
        </Card>

        <LiveCommunicationButton onPress={() => router.push('/live')} />
      </View>
    </MainAppScreen>
  );
}

const styles = StyleSheet.create({
  content: { paddingBottom: spacing.lgPlus },
  greeting: {
    minHeight: 52,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: spacing.section,
  },
  greetingCopy: { gap: spacing.sm },
  title: {
    fontFamily: fontFamilies.bold,
    fontSize: 26,
    lineHeight: 28,
    letterSpacing: -0.4,
  },
  subtitle: { fontSize: 12, lineHeight: 16 },
  headerWavesFrame: {
    width: 135,
    height: 42,
    overflow: 'hidden',
  },
  headerWaves: {
    position: 'absolute',
    top: -5,
    left: -17,
    width: 163,
    height: 58,
  },
  overviewSection: { gap: spacing.md, marginTop: spacing.section },
  cardPressable: { borderRadius: radii.card },
  pressed: { opacity: 0.76 },
  statusCard: {
    height: 80,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: spacing.md,
  },
  statusLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.lg,
  },
  statusIcon: {
    width: 48,
    height: 48,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: radii.full,
    backgroundColor: colors.background,
  },
  statusCopy: { gap: 5 },
  cardTitle: {
    fontFamily: fontFamilies.semiBold,
    fontSize: 12,
    lineHeight: 15,
  },
  cardDescription: {
    fontFamily: fontFamilies.medium,
    fontSize: 9,
    lineHeight: 10,
  },
  metrics: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.md,
  },
  metricCard: { width: 165, height: 71, flexGrow: 1, flexBasis: 150 },
  communicationCard: {
    height: 94,
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.lg,
    padding: spacing.md,
  },
  communicationVisual: {
    width: 70,
    height: 70,
    alignItems: 'center',
    justifyContent: 'center',
  },
  communicationRings: { opacity: 0.7 },
  wearableFrame: {
    position: 'absolute',
    top: 10,
    left: 7,
    width: 57,
    height: 50,
    overflow: 'hidden',
  },
  wearableImage: {
    position: 'absolute',
    top: -43,
    left: -25,
    width: 169,
    height: 113,
  },
  communicationRight: {
    width: 218,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'flex-end',
    gap: spacing.lg,
  },
  communicationCopy: { width: 146, gap: 5 },
  cardWaves: { width: 56, height: 32, flexShrink: 0 },
});
