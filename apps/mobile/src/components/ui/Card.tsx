import {
  StyleSheet,
  View,
  type StyleProp,
  type ViewProps,
  type ViewStyle,
} from 'react-native';

import { colors, radii, spacing } from '@/theme';

type CardProps = Omit<ViewProps, 'style'> & {
  padding?: 'none' | 'small' | 'medium';
  style?: StyleProp<ViewStyle>;
};

export function Card({
  children,
  padding = 'medium',
  style,
  ...props
}: CardProps) {
  return (
    <View style={[styles.base, styles[padding], style]} {...props}>
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  base: {
    backgroundColor: colors.surface,
    borderRadius: radii.card,
  },
  none: { padding: 0 },
  small: { padding: spacing.sm },
  medium: { padding: spacing.md },
});
