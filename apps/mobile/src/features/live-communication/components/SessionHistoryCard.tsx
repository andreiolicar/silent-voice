import { StyleSheet, View } from 'react-native';

import { AppText, Card } from '@/components/ui';
import { spacing } from '@/theme';

import type { ConfirmedUtterance } from '../types/live-session';

type SessionHistoryCardProps = { entries: ConfirmedUtterance[] };

function formatTime(timestamp: number) {
  const date = new Date(timestamp);
  return [date.getUTCHours(), date.getUTCMinutes()]
    .map((part) => String(part).padStart(2, '0'))
    .join(':');
}

export function SessionHistoryCard({ entries }: SessionHistoryCardProps) {
  const recent = entries.slice(-3);

  return (
    <Card style={styles.card}>
      <AppText style={styles.title} variant="cardTitle">
        Histórico da sessão
      </AppText>
      <View style={styles.entries}>
        {recent.length ? (
          recent.map((entry) => (
            <View key={entry.id} style={styles.entry}>
              <AppText style={styles.time} tone="secondary" variant="caption">
                {formatTime(entry.timestamp)}
              </AppText>
              <AppText style={styles.text} variant="bodySmall">
                “{entry.text}”
              </AppText>
            </View>
          ))
        ) : (
          <AppText tone="secondary" variant="bodySmall">
            As intenções confirmadas aparecerão aqui.
          </AppText>
        )}
      </View>
    </Card>
  );
}

const styles = StyleSheet.create({
  card: { gap: spacing.smPlus, padding: spacing.md },
  title: { fontSize: 12, lineHeight: 15 },
  entries: { gap: spacing.sm },
  entry: { flexDirection: 'row', alignItems: 'baseline', gap: spacing.md },
  time: { width: 36, flexShrink: 0, fontSize: 10 },
  text: { minWidth: 0, flex: 1, fontSize: 11, lineHeight: 16 },
});
