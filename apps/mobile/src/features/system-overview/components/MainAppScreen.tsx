import { useRouter } from 'expo-router';
import type { PropsWithChildren } from 'react';
import {
  Platform,
  ScrollView,
  StyleSheet,
  View,
  type StyleProp,
  type ViewStyle,
} from 'react-native';

import {
  BottomNavigation,
  type BottomNavigationItem,
  Screen,
} from '@/components/layout';
import { spacing } from '@/theme';

type MainAppScreenProps = PropsWithChildren<{
  activeItem?: BottomNavigationItem;
  contentStyle?: StyleProp<ViewStyle>;
  showBottomNavigation?: boolean;
}>;

export function MainAppScreen({
  activeItem = 'home',
  children,
  contentStyle,
  showBottomNavigation = true,
}: MainAppScreenProps) {
  const router = useRouter();

  const handleNavigation = (item: BottomNavigationItem) => {
    const routes = {
      home: '/home',
      hub: '/hub',
      communication: '/live',
      history: '/history',
      settings: '/settings',
    } as const;

    router.replace(routes[item]);
  };

  return (
    <Screen contentStyle={styles.screen} padded={false}>
      <View style={styles.frame}>
        <ScrollView
          contentContainerStyle={[styles.content, contentStyle]}
          contentInsetAdjustmentBehavior="automatic"
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
          style={styles.scroll}
        >
          {children}
        </ScrollView>
        {showBottomNavigation ? (
          <View style={styles.navigation}>
            <BottomNavigation
              activeItem={activeItem}
              onItemPress={handleNavigation}
            />
          </View>
        ) : null}
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  screen: { width: '100%', flex: 1, alignItems: 'center' },
  frame: { width: '100%', maxWidth: 402, minHeight: 0, flex: 1 },
  scroll: { minHeight: 0, flex: 1 },
  content: {
    flexGrow: 1,
    paddingTop: Platform.select({ web: 75, default: 18 }),
    paddingHorizontal: spacing.screen,
    paddingBottom: spacing.lgPlus,
  },
  navigation: {
    paddingHorizontal: spacing.screen,
    paddingBottom: spacing.screen,
  },
});
