import type { PropsWithChildren } from 'react';
import {
  ImageBackground,
  ScrollView,
  StyleSheet,
  View,
  type ImageSourcePropType,
  type ImageStyle,
  type StyleProp,
  type ViewStyle,
} from 'react-native';

import { Screen } from '@/components/layout';
import { spacing } from '@/theme';

type InitialFlowScreenProps = PropsWithChildren<{
  background?: ImageSourcePropType | null;
  backgroundStyle?: StyleProp<ImageStyle>;
  contentStyle?: StyleProp<ViewStyle>;
  scroll?: boolean;
}>;

export function InitialFlowScreen({
  background = null,
  backgroundStyle,
  children,
  contentStyle,
  scroll = true,
}: InitialFlowScreenProps) {
  const content = (
    <View style={styles.contentFrame}>
      {background ? (
        <ImageBackground
          resizeMode="cover"
          source={background}
          style={[StyleSheet.absoluteFill, backgroundStyle]}
        />
      ) : null}
      <View style={[styles.content, contentStyle]}>{children}</View>
    </View>
  );

  return (
    <Screen contentStyle={styles.screen} padded={false}>
      {scroll ? (
        <ScrollView
          contentContainerStyle={styles.scrollContent}
          showsVerticalScrollIndicator={false}
        >
          {content}
        </ScrollView>
      ) : (
        content
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1 },
  scrollContent: { flexGrow: 1 },
  contentFrame: {
    width: '100%',
    maxWidth: 402,
    flexGrow: 1,
    alignSelf: 'center',
    overflow: 'hidden',
  },
  content: {
    flexGrow: 1,
    paddingHorizontal: spacing.screen,
    paddingTop: spacing.lg,
    paddingBottom: spacing.lgPlus,
  },
});
