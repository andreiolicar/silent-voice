import { Volume2 } from 'lucide-react-native';
import { StyleSheet, View } from 'react-native';

import { AppText } from '@/components/ui';
import { colors, radii, spacing } from '@/theme';

import { formatCommunicationTime } from '../data/group-communication-history';
import type { CommunicationHistoryEntry } from '../types/communication-history';

type HistoryEntryProps = {
  entry: CommunicationHistoryEntry;
};

export function HistoryEntry({ entry }: HistoryEntryProps) {
  const time = formatCommunicationTime(entry.confirmedAt);

  return (
    <View
      accessibilityLabel={`${time}. ${entry.text}`}
      style={styles.container}
    >
      <View style={styles.iconFrame}>
        <Volume2 color={colors.accent} size={18} strokeWidth={1.8} />
      </View>
      <View style={styles.copy}>
        <AppText tone="secondary" variant="caption">
          {time}
        </AppText>
        <AppText variant="body">“{entry.text}”</AppText>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    minHeight: 58,
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    paddingVertical: spacing.sm,
  },
  iconFrame: {
    width: 36,
    height: 36,
    flexShrink: 0,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: radii.full,
    backgroundColor: colors.background,
  },
  copy: { minWidth: 0, flex: 1, gap: spacing.xxs },
});
