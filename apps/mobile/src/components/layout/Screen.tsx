import { StatusBar } from 'expo-status-bar';
import type { PropsWithChildren } from 'react';
import {
  ScrollView,
  StyleSheet,
  View,
  type StyleProp,
  type ViewStyle,
} from 'react-native';
import { SafeAreaView, type Edge } from 'react-native-safe-area-context';

import { colors, spacing } from '@/theme';

type ScreenProps = PropsWithChildren<{
  contentStyle?: StyleProp<ViewStyle>;
  edges?: Edge[];
  padded?: boolean;
  scroll?: boolean;
}>;

export function Screen({
  children,
  contentStyle,
  edges = ['top', 'right', 'bottom', 'left'],
  padded = true,
  scroll = false,
}: ScreenProps) {
  const resolvedContentStyle = [
    styles.content,
    padded && styles.padded,
    contentStyle,
  ];

  return (
    <SafeAreaView edges={edges} style={styles.safeArea}>
      <StatusBar style="dark" />
      {scroll ? (
        <ScrollView
          contentContainerStyle={resolvedContentStyle}
          contentInsetAdjustmentBehavior="automatic"
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
        >
          {children}
        </ScrollView>
      ) : (
        <View style={resolvedContentStyle}>{children}</View>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: colors.background },
  content: { flexGrow: 1 },
  padded: {
    paddingHorizontal: spacing.screen,
    paddingVertical: spacing.lg,
  },
});
