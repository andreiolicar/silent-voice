import {
  Activity,
  Cpu,
  Thermometer,
  TrendingUp,
  Zap,
  type LucideIcon,
} from 'lucide-react-native';
import { useRouter } from 'expo-router';
import { Image, StyleSheet, View } from 'react-native';

import { PrivacyNotice, StatusBadge } from '@/components/silent-voice';
import { AppText, Card } from '@/components/ui';
import { colors, fontFamilies, radii, spacing } from '@/theme';

import { HealthMetricCard } from '../components/HealthMetricCard';
import { MainAppScreen } from '../components/MainAppScreen';
import { SystemAppHeader } from '../components/SystemAppHeader';
import {
  systemHealthMock,
  type HealthMetric,
} from '../data/system-overview.mock';

const stabilityChart = require('@/assets/images/system-overview/system-stability-chart.png');

const healthIcons: Record<HealthMetric['icon'], LucideIcon> = {
  activity: Activity,
  cpu: Cpu,
  power: Zap,
  thermometer: Thermometer,
};

export default function SystemHealthScreen() {
  const router = useRouter();

  return (
    <MainAppScreen>
      <SystemAppHeader onBack={() => router.replace('/home')} />

      <View style={styles.heading}>
        <AppText style={styles.title}>Saúde do sistema</AppText>
        <AppText style={styles.subtitle} tone="secondary">
          Desempenho do hardware em tempo real.
        </AppText>
      </View>

      <View style={styles.section}>
        <View style={styles.metrics}>
          {systemHealthMock.metrics.map((metric) => (
            <HealthMetricCard
              icon={healthIcons[metric.icon]}
              key={metric.id}
              metric={metric}
            />
          ))}
        </View>

        <Card style={styles.stabilityCard}>
          <View style={styles.stabilityHeader}>
            <View style={styles.stabilityLeft}>
              <View style={styles.stabilityIcon}>
                <TrendingUp color={colors.accent} size={16} />
              </View>
              <View style={styles.stabilityCopy}>
                <AppText style={styles.stabilityTitle}>
                  {systemHealthMock.stability.title}
                </AppText>
                <AppText style={styles.stabilityDescription} tone="secondary">
                  {systemHealthMock.stability.description}
                </AppText>
              </View>
            </View>
            <StatusBadge
              iconPosition="end"
              label={systemHealthMock.stability.status}
              size="compact"
              style={styles.stabilityBadge}
            />
          </View>
          <Image
            accessibilityLabel="Gráfico de estabilidade na última hora"
            resizeMode="stretch"
            source={stabilityChart}
            style={styles.chart}
          />
        </Card>

        <PrivacyNotice compact text={systemHealthMock.privacy} />
      </View>
    </MainAppScreen>
  );
}

const styles = StyleSheet.create({
  heading: { gap: spacing.sm, marginTop: spacing.section },
  title: {
    fontFamily: fontFamilies.bold,
    fontSize: 26,
    lineHeight: 28,
    letterSpacing: -0.4,
  },
  subtitle: { fontSize: 12, lineHeight: 16 },
  section: { gap: spacing.md, marginTop: spacing.section },
  metrics: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.md },
  stabilityCard: { gap: spacing.lgPlus, padding: spacing.md },
  stabilityHeader: {
    minHeight: 32,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  stabilityLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
  },
  stabilityIcon: {
    width: 32,
    height: 32,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: radii.full,
    backgroundColor: colors.background,
  },
  stabilityCopy: { gap: 5 },
  stabilityTitle: {
    fontFamily: fontFamilies.semiBold,
    fontSize: 12,
    lineHeight: 15,
  },
  stabilityDescription: {
    fontFamily: fontFamilies.medium,
    fontSize: 9,
    lineHeight: 10,
  },
  stabilityBadge: { paddingHorizontal: spacing.smPlus },
  chart: { width: '100%', aspectRatio: 319 / 169 },
});
