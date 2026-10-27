import { Platform, type ViewStyle } from 'react-native';
import { Easing } from 'react-native-reanimated';

import { colors } from './colors';

export const motion = {
  fast: 140,
  normal: 180,
  toggle: 200,
  screen: 220,
  section: 320,
  stagger: 60,
  travel: 20,
  press: 140,
  buttonScale: 0.97,
  cardScale: 0.985,
  selectedScale: 1.08,
  easing: Easing.bezier(0.2, 0, 0, 1),
  easingCss: 'cubic-bezier(0.2, 0, 0, 1)',
} as const;

type WebTransitionStyle = ViewStyle & {
  transitionDuration?: string;
  transitionProperty?: string;
  transitionTimingFunction?: string;
};

type FocusVisibleTarget = {
  matches?: (selector: string) => boolean;
};

export function getWebTransitionStyle(
  reduceMotion: boolean,
  properties: string,
  duration: number = motion.fast,
): WebTransitionStyle {
  if (Platform.OS !== 'web') return {};

  return {
    transitionDuration: `${reduceMotion ? 0 : duration}ms`,
    transitionProperty: properties,
    transitionTimingFunction: motion.easingCss,
  };
}

export function isFocusVisible(event: { currentTarget: unknown }) {
  if (Platform.OS !== 'web') return true;

  const target = event.currentTarget as FocusVisibleTarget;
  return target.matches?.(':focus-visible') ?? false;
}

export const focusRing =
  Platform.select<ViewStyle>({
    web: {
      outlineColor: colors.accent,
      outlineStyle: 'solid',
      outlineWidth: 1,
    },
    default: {},
  }) ?? {};

export const webNoOutline =
  Platform.OS === 'web'
    ? ({ outlineStyle: 'none' } as unknown as ViewStyle)
    : {};
