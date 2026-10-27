import { ArrowLeft, type LucideIcon } from 'lucide-react-native';
import type { ReactNode } from 'react';
import { StyleSheet, View } from 'react-native';

import { spacing } from '@/theme';

import { IconButton } from '../ui/IconButton';

type AppHeaderProps = {
  backAccessibilityLabel?: string;
  backIcon?: LucideIcon;
  compact?: boolean;
  layout?: 'centered' | 'split';
  logo: ReactNode;
  onBack?: () => void;
  right?: ReactNode;
};

export function AppHeader({
  backAccessibilityLabel = 'Voltar',
  backIcon: BackIcon = ArrowLeft,
  compact = false,
  layout = 'centered',
  logo,
  onBack,
  right,
}: AppHeaderProps) {
  const isSplit = layout === 'split' && !onBack;

  return (
    <View
      style={[
        styles.container,
        (isSplit || compact) && styles.compactContainer,
      ]}
    >
      {isSplit ? null : (
        <View style={[styles.leading, compact && styles.compactSide]}>
          {onBack ? (
            <IconButton
              accessibilityLabel={backAccessibilityLabel}
              icon={BackIcon}
              iconSize={compact ? 14 : undefined}
              onPress={onBack}
              size={compact ? 'compact' : 'medium'}
              style={compact ? styles.compactBack : undefined}
              variant="ghost"
            />
          ) : null}
        </View>
      )}
      <View style={[styles.logo, isSplit && styles.splitLogo]}>{logo}</View>
      <View style={[styles.trailing, compact && styles.compactSide]}>
        {right}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    minHeight: 52,
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
  },
  compactContainer: { minHeight: 30 },
  leading: {
    width: 44,
    alignItems: 'center',
    justifyContent: 'center',
  },
  trailing: {
    width: 44,
    alignItems: 'flex-end',
    justifyContent: 'center',
  },
  compactSide: { width: 30 },
  compactBack: {
    width: 30,
    height: 30,
    backgroundColor: 'rgba(26, 169, 155, 0.25)',
  },
  logo: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  splitLogo: { alignItems: 'flex-start' },
});
