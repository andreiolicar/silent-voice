import { useState } from 'react';
import { StyleSheet, TextInput, View, type TextInputProps } from 'react-native';
import { AppText } from './AppText';
import { colors, fontFamilies, radii, spacing } from '@/theme';

type Props = TextInputProps & { label: string; error?: string };
export function TextField({ label, error, style, ...props }: Props) {
  const [focused, setFocused] = useState(false);
  return (
    <View style={styles.group}>
      <AppText variant="body">{label}</AppText>
      <TextInput
        accessibilityLabel={label}
        accessibilityHint={error}
        autoCapitalize="none"
        placeholderTextColor={colors.textSecondary}
        {...props}
        onFocus={(e) => {
          setFocused(true);
          props.onFocus?.(e);
        }}
        onBlur={(e) => {
          setFocused(false);
          props.onBlur?.(e);
        }}
        style={[
          styles.input,
          focused && styles.focused,
          error && styles.error,
          style,
        ]}
      />
      {error ? (
        <AppText accessibilityRole="alert" tone="error">
          {error}
        </AppText>
      ) : null}
    </View>
  );
}
const styles = StyleSheet.create({
  group: { gap: spacing.sm },
  input: {
    minHeight: 48,
    padding: spacing.md,
    borderWidth: 1,
    borderColor: colors.borderStrong,
    borderRadius: radii.control,
    fontFamily: fontFamilies.regular,
    fontSize: 16,
    color: colors.primary,
    backgroundColor: colors.surface,
  },
  focused: { borderColor: colors.accent, borderWidth: 2 },
  error: { borderColor: colors.error },
});
