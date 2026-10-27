import {
  Boxes,
  History,
  House,
  Radio,
  Settings2,
  type LucideIcon,
} from 'lucide-react-native';
import { useState } from 'react';
import { Pressable, StyleSheet, View, type TextStyle } from 'react-native';

import { useReducedMotion } from '@/hooks/useReducedMotion';
import {
  colors,
  getWebTransitionStyle,
  isFocusVisible,
  motion,
  radii,
  spacing,
  webNoOutline,
} from '@/theme';

import { AppText } from '../ui/AppText';

export type BottomNavigationItem =
  'home' | 'hub' | 'communication' | 'history' | 'settings';

type BottomNavigationProps = {
  activeItem: BottomNavigationItem;
  onItemPress: (item: BottomNavigationItem) => void;
};

type NavigationItem = {
  icon: LucideIcon;
  id: BottomNavigationItem;
  label: string;
};

const items: NavigationItem[] = [
  { id: 'home', label: 'Início', icon: House },
  { id: 'hub', label: 'Hub', icon: Boxes },
  { id: 'communication', label: 'Comunicação', icon: Radio },
  { id: 'history', label: 'Histórico', icon: History },
  { id: 'settings', label: 'Ajustes', icon: Settings2 },
];

export function BottomNavigation({
  activeItem,
  onItemPress,
}: BottomNavigationProps) {
  const [focusedItem, setFocusedItem] = useState<BottomNavigationItem | null>(
    null,
  );
  const [hoveredItem, setHoveredItem] = useState<BottomNavigationItem | null>(
    null,
  );
  const reduceMotion = useReducedMotion();

  return (
    <View accessibilityRole="tablist" style={styles.container}>
      {items.map(({ icon: Icon, id, label }) => {
        const isActive = activeItem === id;
        const isCommunication = id === 'communication';
        const isFocused = focusedItem === id;
        const isHovered = hoveredItem === id;
        const hasHoverFeedback = isHovered && !isActive;
        const hasTextHoverFeedback = !isCommunication && hasHoverFeedback;

        return (
          <Pressable
            accessibilityLabel={label}
            accessibilityRole="tab"
            accessibilityState={{ selected: isActive }}
            aria-selected={isActive}
            key={id}
            onBlur={() => setFocusedItem(null)}
            onFocus={(event) =>
              setFocusedItem(isFocusVisible(event) ? id : null)
            }
            onHoverIn={() => setHoveredItem(id)}
            onHoverOut={() => setHoveredItem(null)}
            onPress={() => onItemPress(id)}
            style={({ pressed }) => [
              styles.item,
              webNoOutline,
              getWebTransitionStyle(reduceMotion, 'opacity'),
              pressed && styles.pressed,
            ]}
          >
            <View
              style={[
                styles.iconContainer,
                isCommunication && styles.communication,
                hasHoverFeedback &&
                  isCommunication &&
                  styles.communicationHovered,
                isFocused && isCommunication && styles.communicationFocused,
                getWebTransitionStyle(
                  reduceMotion,
                  'background-color, opacity',
                ),
              ]}
            >
              <Icon
                color={
                  isCommunication
                    ? colors.white
                    : isFocused
                      ? colors.accent
                      : isActive || hasTextHoverFeedback
                        ? colors.primary
                        : colors.textSecondary
                }
                size={20}
                style={getWebTransitionStyle(
                  reduceMotion,
                  'color, stroke',
                  motion.normal,
                )}
                strokeWidth={isActive || isFocused ? 2.5 : 2}
              />
            </View>
            {isCommunication ? null : (
              <AppText
                style={[
                  isActive && styles.activeLabel,
                  getWebTransitionStyle(
                    reduceMotion,
                    'color',
                    motion.normal,
                  ) as unknown as TextStyle,
                ]}
                tone={
                  isFocused
                    ? 'accent'
                    : isActive || hasTextHoverFeedback
                      ? 'primary'
                      : 'secondary'
                }
                variant="navigation"
              >
                {label}
              </AppText>
            )}
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    width: '100%',
    minHeight: 72,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: spacing.lgPlus,
    paddingVertical: spacing.smPlus,
    borderRadius: radii.full,
    backgroundColor: colors.surface,
  },
  item: {
    minWidth: 44,
    minHeight: 48,
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.xs,
    borderRadius: radii.control,
  },
  iconContainer: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  communication: {
    width: 52,
    height: 52,
    borderRadius: radii.full,
    backgroundColor: colors.accent,
  },
  communicationHovered: { opacity: 0.88 },
  communicationFocused: { opacity: 0.78 },
  activeLabel: { color: colors.primary },
  pressed: { opacity: 0.65 },
});
