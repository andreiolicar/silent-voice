import { ChevronRight, Radio } from 'lucide-react-native';
import { StyleSheet, View } from 'react-native';

import { Button } from '@/components/ui';
import { colors, spacing } from '@/theme';

type LiveCommunicationButtonProps = { onPress?: () => void };

export function LiveCommunicationButton({
  onPress,
}: LiveCommunicationButtonProps) {
  return (
    <View style={styles.frame}>
      <Button
        contentStyle={styles.content}
        iconSize={14}
        label="Abrir comunicação ao vivo"
        labelStyle={styles.label}
        leftIcon={Radio}
        leftIconBackgroundColor="rgba(123, 228, 219, 0.5)"
        onPress={onPress}
        style={styles.button}
      />
      <ChevronRight color={colors.white} size={18} style={styles.chevron} />
    </View>
  );
}

const styles = StyleSheet.create({
  frame: { height: 42 },
  button: { height: 42, minHeight: 42 },
  content: { width: '100%', gap: spacing.smPlus },
  label: { fontSize: 12, lineHeight: 22 },
  chevron: {
    position: 'absolute',
    top: 12,
    right: 35,
    pointerEvents: 'none',
  },
});
