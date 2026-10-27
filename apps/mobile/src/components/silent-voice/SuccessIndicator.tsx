import { Check } from 'lucide-react-native';
import { StyleSheet, View } from 'react-native';

import { colors, radii } from '@/theme';

type SuccessIndicatorProps = { size?: number };

export function SuccessIndicator({ size = 24 }: SuccessIndicatorProps) {
  return (
    <View style={[styles.indicator, { width: size, height: size }]}>
      <Check
        color={colors.white}
        size={Math.round(size * 0.5)}
        strokeWidth={3}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  indicator: {
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: radii.full,
    backgroundColor: colors.accent,
  },
});
