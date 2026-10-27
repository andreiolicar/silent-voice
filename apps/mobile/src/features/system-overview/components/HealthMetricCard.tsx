import type { LucideIcon } from 'lucide-react-native';
import { StyleSheet, View } from 'react-native';

import { StatusBadge } from '@/components/silent-voice';
import { AppText, Card } from '@/components/ui';
import { colors, fontFamilies, radii, spacing } from '@/theme';

import type { HealthMetric } from '../data/system-overview.mock';

type HealthMetricCardProps = {
  icon: LucideIcon;
  metric: HealthMetric;
};

export function HealthMetricCard({
  icon: Icon,
  metric,
}: HealthMetricCardProps) {
  const value =
    metric.value.state === 'available'
      ? metric.value.text
      : metric.value.state === 'unknown'
        ? 'Desconhecido'
        : 'Indisponível';

  return (
    <Card accessibilityLabel={`${metric.label}: ${value}`} style={styles.card}>
      <View style={styles.header}>
        <View style={styles.icon}>
          <View style={styles.unrotatedIcon}>
            <Icon color={colors.accent} size={26} />
          </View>
        </View>
        <View style={styles.copy}>
          <AppText
            numberOfLines={1}
            style={[
              styles.label,
              metric.id === 'processor' && styles.processorLabel,
            ]}
          >
            {metric.label}
          </AppText>
          <AppText style={styles.value} tone="accent">
            {value}
          </AppText>
        </View>
      </View>

      {metric.progress !== undefined ? (
        <View style={styles.progressTrack}>
          <View
            style={[
              styles.progressFill,
              { width: `${Math.round(metric.progress * 100)}%` },
            ]}
          />
        </View>
      ) : null}

      {metric.description ? (
        <AppText style={styles.description} tone="secondary">
          {metric.description}
        </AppText>
      ) : null}

      {metric.status ? (
        <StatusBadge
          label={metric.status}
          size="compact"
          style={styles.status}
        />
      ) : null}
    </Card>
  );
}

const styles = StyleSheet.create({
  card: {
    width: 165,
    height: 106,
    flexGrow: 1,
    flexBasis: 150,
    alignItems: 'flex-start',
    gap: spacing.smPlus,
    padding: spacing.md,
  },
  header: { flexDirection: 'row', alignItems: 'center', gap: spacing.lg },
  icon: {
    width: 46,
    height: 46,
    alignItems: 'center',
    justifyContent: 'center',
    overflow: 'hidden',
    borderRadius: radii.full,
    backgroundColor: colors.background,
  },
  unrotatedIcon: {},
  copy: { flexShrink: 1, gap: 5 },
  label: {
    fontFamily: fontFamilies.semiBold,
    fontSize: 12,
    lineHeight: 15,
  },
  processorLabel: { fontSize: 10.5 },
  value: {
    fontFamily: fontFamilies.semiBold,
    fontSize: 16,
    lineHeight: 15,
  },
  progressTrack: {
    width: '100%',
    height: 6,
    overflow: 'hidden',
    borderRadius: radii.full,
    backgroundColor: 'rgba(26, 169, 155, 0.25)',
  },
  progressFill: {
    height: 6,
    borderRadius: radii.full,
    backgroundColor: colors.accent,
  },
  description: {
    fontFamily: fontFamilies.medium,
    fontSize: 9,
    lineHeight: 10,
  },
  status: { width: '100%' },
});
