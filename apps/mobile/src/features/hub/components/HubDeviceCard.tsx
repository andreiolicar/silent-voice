import { Usb } from 'lucide-react-native';
import { StyleSheet, View } from 'react-native';

import { StatusBadge } from '@/components/silent-voice';
import { AppText, Card } from '@/components/ui';
import { colors, radii, spacing } from '@/theme';

type HubDeviceCardProps = {
  connected: boolean;
  gateway: string;
  name: string;
  transport: 'USB';
};

export function HubDeviceCard({
  connected,
  gateway,
  name,
  transport,
}: HubDeviceCardProps) {
  const status = connected ? 'Conectado' : 'Desconectado';

  return (
    <Card
      accessibilityLabel={`${name}. ${gateway}. ${status} por ${transport}.`}
      style={styles.card}
    >
      <View style={styles.iconFrame}>
        <Usb color={colors.accent} size={24} strokeWidth={1.7} />
      </View>
      <View style={styles.copy}>
        <AppText variant="cardTitle">{name}</AppText>
        <AppText tone="secondary" variant="caption">
          {gateway}
        </AppText>
      </View>
      <View style={styles.connection}>
        <StatusBadge
          label={status}
          size="compact"
          tone={connected ? 'success' : 'neutral'}
        />
        <AppText tone="accent" variant="caption">
          {transport}
        </AppText>
      </View>
    </Card>
  );
}

const styles = StyleSheet.create({
  card: {
    minHeight: 82,
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
  },
  iconFrame: {
    width: 48,
    height: 48,
    flexShrink: 0,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: radii.full,
    backgroundColor: colors.background,
  },
  copy: { minWidth: 0, flex: 1, gap: spacing.xs },
  connection: { alignItems: 'flex-end', gap: spacing.xs },
});
