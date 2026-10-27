import type { LucideIcon } from 'lucide-react-native';
import { StyleSheet, View } from 'react-native';

import { colors, fontFamilies, radii, spacing } from '@/theme';

import { AppText } from '../ui/AppText';
import { Badge } from '../ui/Badge';
import { Card } from '../ui/Card';

type DeviceCardProps = {
  description: string;
  icon: LucideIcon;
  name: string;
  status: string;
  statusTone?: 'error' | 'neutral' | 'success';
};

export function DeviceCard({
  description,
  icon: Icon,
  name,
  status,
  statusTone = 'neutral',
}: DeviceCardProps) {
  return (
    <Card
      accessibilityLabel={`${name}. ${description}. ${status}.`}
      style={styles.card}
    >
      <View style={styles.icon}>
        <Icon color={colors.accent} size={24} strokeWidth={1.6} />
      </View>
      <View style={styles.content}>
        <AppText style={styles.name}>{name}</AppText>
        <AppText style={styles.description} tone="secondary">
          {description}
        </AppText>
      </View>
      <Badge size="regular" tone={statusTone}>
        {status}
      </Badge>
    </Card>
  );
}

const styles = StyleSheet.create({
  card: {
    minHeight: 72,
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    padding: spacing.md,
  },
  icon: {
    width: 44,
    height: 44,
    flexShrink: 0,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: radii.full,
    backgroundColor: colors.background,
  },
  content: { minWidth: 0, flex: 1, gap: spacing.xs },
  name: {
    fontFamily: fontFamilies.semiBold,
    fontSize: 12,
    lineHeight: 15,
  },
  description: {
    fontFamily: fontFamilies.medium,
    fontSize: 9,
    lineHeight: 12,
  },
});
