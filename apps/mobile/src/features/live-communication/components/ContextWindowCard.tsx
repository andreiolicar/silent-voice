import { MessageCircleMore } from 'lucide-react-native';
import { Image, StyleSheet, View } from 'react-native';

import { Card, AppText } from '@/components/ui';
import { colors, radii, spacing } from '@/theme';

import type { ContextTranscriptEntry } from '../types/live-session';

const contextWaveform = require('@/assets/images/live-communication/context-waveform.png');

type ContextWindowCardProps = { entries: ContextTranscriptEntry[] };

function formatTime(timestamp: number) {
  const date = new Date(timestamp);
  return [date.getUTCHours(), date.getUTCMinutes(), date.getUTCSeconds()]
    .map((part) => String(part).padStart(2, '0'))
    .join(':');
}

export function ContextWindowCard({ entries }: ContextWindowCardProps) {
  return (
    <Card style={styles.card}>
      <View style={styles.header}>
        <View style={styles.headerLeft}>
          <View style={styles.iconContainer}>
            <MessageCircleMore color={colors.textSecondary} size={16} />
          </View>
          <View style={styles.titleGroup}>
            <AppText style={styles.title} variant="cardTitle">
              Contexto do ambiente
            </AppText>
            <AppText style={styles.subtitle} tone="secondary">
              Transcrição recente da fala ambiente
            </AppText>
          </View>
        </View>
        <View style={styles.windowBadge}>
          <AppText style={styles.windowText} tone="secondary" variant="caption">
            Últimos 10s
          </AppText>
        </View>
      </View>

      <View style={styles.entries}>
        {entries.map((entry) => (
          <View key={entry.id} style={styles.entry}>
            <AppText
              style={styles.timestamp}
              tone="secondary"
              variant="caption"
            >
              {formatTime(entry.timestamp)}
            </AppText>
            <AppText
              style={styles.transcript}
              tone="secondary"
              variant="caption"
            >
              {entry.text}
            </AppText>
          </View>
        ))}
      </View>

      <View style={styles.waveformFrame}>
        <Image
          resizeMode="cover"
          source={contextWaveform}
          style={styles.waveform}
        />
      </View>
    </Card>
  );
}

const styles = StyleSheet.create({
  card: { gap: spacing.lgPlus, padding: spacing.md },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing.md,
  },
  headerLeft: {
    minWidth: 0,
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
  },
  iconContainer: {
    width: 32,
    height: 32,
    flexShrink: 0,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: radii.full,
    backgroundColor: colors.background,
  },
  titleGroup: { minWidth: 0, flex: 1, gap: 3 },
  title: { fontSize: 12, lineHeight: 15 },
  subtitle: { fontSize: 9, lineHeight: 12 },
  windowBadge: {
    minHeight: 22,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: spacing.sm,
    borderWidth: 0.5,
    borderColor: colors.borderStrong,
    borderRadius: radii.control,
    backgroundColor: colors.background,
  },
  windowText: { fontSize: 9, lineHeight: 12 },
  entries: { gap: spacing.sm },
  entry: { flexDirection: 'row', gap: spacing.md },
  timestamp: { width: 54, flexShrink: 0, fontSize: 10, lineHeight: 16 },
  transcript: { minWidth: 0, flex: 1, fontSize: 10, lineHeight: 16 },
  waveformFrame: { height: 18, overflow: 'hidden' },
  waveform: { width: '100%', height: 18, opacity: 0.72 },
});
