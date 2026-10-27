const palette = {
  background: '#F6F5F8',
  surface: '#FFFFFF',
  primaryDark: '#051B34',
  secondaryGreen: '#1AA99B',
  gray1: '#929CAD',
} as const;

export const colors = {
  background: palette.background,
  surface: palette.surface,
  primary: palette.primaryDark,
  accent: palette.secondaryGreen,
  accentSubtle: 'rgba(26, 169, 155, 0.06)',
  accentSoft: 'rgba(26, 169, 155, 0.14)',
  textPrimary: palette.primaryDark,
  textSecondary: palette.gray1,
  border: 'rgba(5, 27, 52, 0.12)',
  borderStrong: 'rgba(5, 27, 52, 0.2)',
  disabled: 'rgba(146, 156, 173, 0.45)',
  overlay: 'rgba(5, 27, 52, 0.48)',
  success: palette.secondaryGreen,
  warning: '#B86B00',
  error: '#C43D4D',
  errorSoft: 'rgba(196, 61, 77, 0.12)',
  warningSoft: 'rgba(184, 107, 0, 0.12)',
  white: palette.surface,
} as const;
