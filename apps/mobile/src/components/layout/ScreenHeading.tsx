import { StyleSheet, View } from 'react-native';

import { spacing } from '@/theme';

import { AppText } from '../ui/AppText';

type ScreenHeadingProps = {
  subtitle?: string;
  title: string;
};

export function ScreenHeading({ subtitle, title }: ScreenHeadingProps) {
  return (
    <View style={styles.container}>
      <AppText variant="screenTitle">{title}</AppText>
      {subtitle ? (
        <AppText tone="secondary" variant="subtitle">
          {subtitle}
        </AppText>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { gap: spacing.xs },
});
