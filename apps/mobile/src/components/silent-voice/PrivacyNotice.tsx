import { Lock } from 'lucide-react-native';
import { StyleSheet, View } from 'react-native';

import { colors, spacing } from '@/theme';

import { AppText } from '../ui/AppText';

type PrivacyNoticeProps = {
  compact?: boolean;
  text: string;
};

export function PrivacyNotice({ compact = false, text }: PrivacyNoticeProps) {
  return (
    <View accessibilityRole="text" style={styles.container}>
      <Lock color={colors.textSecondary} size={compact ? 10 : 14} />
      <AppText
        style={[styles.text, compact && styles.textCompact]}
        tone="secondary"
        variant="caption"
      >
        {text}
      </AppText>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.xs,
  },
  text: { flexShrink: 1, textAlign: 'center' },
  textCompact: { fontSize: 8, lineHeight: 10 },
});
