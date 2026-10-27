import type { TextStyle } from 'react-native';

export const fontFamilies = {
  regular: 'Manrope_400Regular',
  medium: 'Manrope_500Medium',
  semiBold: 'Manrope_600SemiBold',
  bold: 'Manrope_700Bold',
} as const;

export const typography = {
  display: {
    fontFamily: fontFamilies.bold,
    fontSize: 32,
    lineHeight: 38,
  },
  screenTitle: { fontFamily: fontFamilies.bold, fontSize: 26, lineHeight: 32 },
  sectionTitle: {
    fontFamily: fontFamilies.bold,
    fontSize: 18,
    lineHeight: 24,
  },
  subtitle: { fontFamily: fontFamilies.regular, fontSize: 14, lineHeight: 20 },
  cardTitle: {
    fontFamily: fontFamilies.semiBold,
    fontSize: 14,
    lineHeight: 20,
  },
  metric: { fontFamily: fontFamilies.semiBold, fontSize: 18, lineHeight: 24 },
  body: { fontFamily: fontFamilies.regular, fontSize: 14, lineHeight: 20 },
  bodySmall: {
    fontFamily: fontFamilies.regular,
    fontSize: 13,
    lineHeight: 18,
  },
  supporting: { fontFamily: fontFamilies.medium, fontSize: 12, lineHeight: 16 },
  navigation: {
    fontFamily: fontFamilies.semiBold,
    fontSize: 12,
    lineHeight: 16,
  },
  caption: {
    fontFamily: fontFamilies.medium,
    fontSize: 11,
    lineHeight: 16,
  },
  label: {
    fontFamily: fontFamilies.semiBold,
    fontSize: 12,
    lineHeight: 16,
  },
  button: {
    fontFamily: fontFamilies.semiBold,
    fontSize: 14,
    lineHeight: 20,
  },
  badge: {
    fontFamily: fontFamilies.semiBold,
    fontSize: 11,
    lineHeight: 14,
  },
} satisfies Record<string, TextStyle>;

export type TypographyVariant = keyof typeof typography;
