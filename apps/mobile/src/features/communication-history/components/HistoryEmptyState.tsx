import { MessageCircle } from 'lucide-react-native';
import { StyleSheet, View } from 'react-native';

import { AppText, Card } from '@/components/ui';
import { colors, radii, spacing } from '@/theme';

export function HistoryEmptyState() {
  return (
    <Card accessibilityLabel="Nenhuma comunicação ainda" style={styles.card}>
      <View style={styles.iconFrame}>
        <MessageCircle color={colors.accent} size={28} strokeWidth={1.6} />
      </View>
      <View style={styles.copy}>
        <AppText variant="sectionTitle">Nenhuma comunicação ainda</AppText>
        <AppText tone="secondary" variant="bodySmall">
          Suas falas confirmadas aparecerão aqui.
        </AppText>
      </View>
    </Card>
  );
}

const styles = StyleSheet.create({
  card: {
    minHeight: 190,
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.lg,
    padding: spacing.xl,
  },
  iconFrame: {
    width: 56,
    height: 56,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: radii.full,
    backgroundColor: colors.accentSoft,
  },
  copy: { alignItems: 'center', gap: spacing.xs },
});
