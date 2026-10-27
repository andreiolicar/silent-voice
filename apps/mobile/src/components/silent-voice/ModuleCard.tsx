import { X, type LucideIcon } from 'lucide-react-native';
import { StyleSheet, View } from 'react-native';

import { colors, fontFamilies, radii, spacing } from '@/theme';

import { AppText } from '../ui/AppText';
import { Badge } from '../ui/Badge';
import { Card } from '../ui/Card';
import { SuccessIndicator } from './SuccessIndicator';

type ModuleCardProps = {
  detail: string;
  icon: LucideIcon;
  iconSize?: number;
  name: string;
  requirement: 'required';
  state: 'connected' | 'disconnected';
};

export function ModuleCard({
  detail,
  icon: Icon,
  iconSize = 24,
  name,
  state,
}: ModuleCardProps) {
  const isConnected = state === 'connected';
  const stateColor = isConnected ? colors.success : colors.textSecondary;
  const stateLabel = isConnected ? 'Operando' : 'Indisponível';

  return (
    <Card accessibilityLabel={`${name}, ${stateLabel}`} style={styles.card}>
      <View style={styles.iconOutline}>
        <View style={styles.icon}>
          <Icon color={stateColor} size={iconSize} />
        </View>
      </View>
      <View style={styles.content}>
        <View style={styles.headline}>
          <AppText style={styles.name}>{name}</AppText>
          <Badge size="compact" style={styles.requiredBadge} tone="success">
            Essencial
          </Badge>
        </View>
        <View style={styles.state}>
          <View style={[styles.stateDot, { backgroundColor: stateColor }]} />
          <AppText style={[styles.stateText, { color: stateColor }]}>
            {stateLabel}
          </AppText>
        </View>
        <AppText style={styles.detail} tone="secondary">
          {detail}
        </AppText>
      </View>
      {isConnected ? (
        <SuccessIndicator size={20} />
      ) : (
        <View style={styles.disconnectedIndicator}>
          <X color={colors.white} size={10} strokeWidth={3} />
        </View>
      )}
    </Card>
  );
}

const styles = StyleSheet.create({
  card: {
    minHeight: 78,
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.lg,
    padding: spacing.md,
  },
  iconOutline: {
    width: 50,
    height: 50,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 0.5,
    borderColor: colors.background,
    borderRadius: radii.full,
  },
  icon: {
    width: 46,
    height: 46,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: radii.full,
    backgroundColor: colors.background,
  },
  content: { minWidth: 0, flex: 1, alignItems: 'flex-start', gap: spacing.xs },
  headline: { flexDirection: 'row', alignItems: 'center', gap: spacing.md },
  name: {
    flexShrink: 1,
    fontFamily: fontFamilies.semiBold,
    fontSize: 12,
    lineHeight: 15,
  },
  requiredBadge: { backgroundColor: 'rgba(26, 169, 155, 0.3)' },
  state: { flexDirection: 'row', alignItems: 'center', gap: spacing.xxs },
  stateDot: { width: 4, height: 4, borderRadius: radii.full },
  stateText: {
    fontFamily: fontFamilies.medium,
    fontSize: 9,
    lineHeight: 10,
  },
  detail: {
    fontFamily: fontFamilies.medium,
    fontSize: 9,
    lineHeight: 11,
  },
  disconnectedIndicator: {
    width: 20,
    height: 20,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: radii.full,
    backgroundColor: colors.textSecondary,
  },
});
