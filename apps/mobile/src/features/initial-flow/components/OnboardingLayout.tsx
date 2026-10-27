import type { PropsWithChildren } from 'react';
import { StyleSheet, View } from 'react-native';

import { AppText } from '@/components/ui';
import { colors, spacing } from '@/theme';

import { BrandLogo } from './BrandLogo';
import { InitialFlowScreen } from './InitialFlowScreen';
import { OnboardingFooter } from './OnboardingFooter';

type OnboardingLayoutProps = PropsWithChildren<{
  align?: 'left' | 'center';
  currentPage: 1 | 2 | 3;
  onContinue: () => void;
  onSkip: () => void;
  subtitle: string;
  title: string;
}>;

export function OnboardingLayout({
  align = 'center',
  children,
  currentPage,
  onContinue,
  onSkip,
  subtitle,
  title,
}: OnboardingLayoutProps) {
  return (
    <InitialFlowScreen>
      <BrandLogo style={styles.logo} />
      <View style={[styles.heading, align === 'left' && styles.headingLeft]}>
        <AppText
          style={[styles.title, align === 'left' && styles.textLeft]}
          variant="screenTitle"
        >
          {title}
          <AppText style={styles.period} variant="screenTitle">
            .
          </AppText>
        </AppText>
        <AppText
          style={align === 'left' ? styles.textLeft : styles.subtitle}
          tone="secondary"
          variant="supporting"
        >
          {subtitle}
        </AppText>
      </View>
      <View style={styles.body}>{children}</View>
      <View style={styles.spacer} />
      <OnboardingFooter
        currentPage={currentPage}
        onContinue={onContinue}
        onSkip={onSkip}
      />
    </InitialFlowScreen>
  );
}

const styles = StyleSheet.create({
  logo: { alignSelf: 'center', marginBottom: spacing.xl },
  heading: { alignItems: 'center', gap: spacing.sm },
  headingLeft: { alignItems: 'flex-start' },
  title: { textAlign: 'center' },
  subtitle: { textAlign: 'center' },
  textLeft: { textAlign: 'left' },
  period: { color: colors.accent },
  body: { paddingTop: spacing.xl },
  spacer: { flexGrow: 1, minHeight: spacing.md },
});
