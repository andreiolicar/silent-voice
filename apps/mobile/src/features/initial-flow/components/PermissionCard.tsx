import type { LucideIcon } from 'lucide-react-native';
import { StyleSheet, View } from 'react-native';

import { AppText, Card, Toggle } from '@/components/ui';
import { colors, fontFamilies, radii } from '@/theme';

type PermissionCardBaseProps = {
  description: string;
  icon: LucideIcon;
  label: string;
};

type PermissionCardProps = PermissionCardBaseProps &
  (
    | {
        enabled: boolean;
        onChange: (enabled: boolean) => void;
        variant: 'toggle';
      }
    | {
        enabled?: never;
        onChange?: never;
        variant: 'informational';
      }
  );

export function PermissionCard({
  description,
  enabled,
  icon: Icon,
  label,
  onChange,
  variant,
}: PermissionCardProps) {
  return (
    <Card style={styles.card}>
      <View style={styles.icon}>
        <Icon color={colors.accent} size={24} strokeWidth={1.5} />
      </View>
      <View style={styles.copy}>
        <AppText style={styles.label}>{label}</AppText>
        <AppText style={styles.description} tone="secondary">
          {description}
        </AppText>
      </View>
      {variant === 'toggle' ? (
        <Toggle
          accessibilityLabel={`Permitir ${label}`}
          onValueChange={onChange}
          size="compact"
          value={enabled}
        />
      ) : (
        <AppText style={styles.informational} tone="accent" variant="caption">
          Ao conectar
        </AppText>
      )}
    </Card>
  );
}

const styles = StyleSheet.create({
  card: {
    minHeight: 68,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 16,
    padding: 12,
  },
  icon: {
    width: 44,
    height: 44,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: radii.full,
    backgroundColor: colors.background,
  },
  copy: { flex: 1, gap: 5 },
  label: {
    fontFamily: fontFamilies.semiBold,
    fontSize: 12,
    lineHeight: 15,
  },
  description: {
    fontFamily: fontFamilies.medium,
    fontSize: 9,
    lineHeight: 10,
  },
  informational: { flexShrink: 0, fontSize: 9, lineHeight: 12 },
});
