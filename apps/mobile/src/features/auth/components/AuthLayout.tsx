import type { PropsWithChildren } from 'react';
import { StyleSheet, View, KeyboardAvoidingView, Platform } from 'react-native';
import { AppText } from '@/components/ui';
import {
  BrandLogo,
  InitialFlowScreen,
} from '@/features/initial-flow/components';
import { spacing } from '@/theme';
export function AuthLayout({
  title,
  subtitle,
  children,
}: PropsWithChildren<{ title: string; subtitle?: string }>) {
  return (
    <InitialFlowScreen>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <View style={styles.content}>
          <BrandLogo />
          <AppText accessibilityRole="header" variant="screenTitle">
            {title}
          </AppText>
          {subtitle ? <AppText tone="secondary">{subtitle}</AppText> : null}
          {children}
        </View>
      </KeyboardAvoidingView>
    </InitialFlowScreen>
  );
}
const styles = StyleSheet.create({
  content: { gap: spacing.lg, paddingVertical: spacing.lg },
});
