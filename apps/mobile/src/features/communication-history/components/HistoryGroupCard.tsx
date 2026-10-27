import { StyleSheet, View } from 'react-native';

import { AppText, Card } from '@/components/ui';
import { colors, spacing } from '@/theme';

import type { CommunicationHistoryGroup } from '../types/communication-history';
import { HistoryEntry } from './HistoryEntry';

type HistoryGroupCardProps = {
  group: CommunicationHistoryGroup;
};

export function HistoryGroupCard({ group }: HistoryGroupCardProps) {
  return (
    <View style={styles.group}>
      <AppText variant="cardTitle">{group.label}</AppText>
      <Card style={styles.card}>
        {group.entries.map((entry, index) => (
          <View key={entry.id}>
            {index > 0 ? <View style={styles.divider} /> : null}
            <HistoryEntry entry={entry} />
          </View>
        ))}
      </Card>
    </View>
  );
}

const styles = StyleSheet.create({
  group: { gap: spacing.sm },
  card: { paddingVertical: spacing.xxs },
  divider: { height: 1, backgroundColor: colors.border },
});
