import { Undo2 } from 'lucide-react-native';
import { Image, StyleSheet, View } from 'react-native';

import { AppHeader } from '@/components/layout';
import { AppText } from '@/components/ui';
import { colors, radii } from '@/theme';

import { homeOverviewMock } from '../data/system-overview.mock';

const logo = require('@/assets/images/initial-flow/logo-full.png');

type SystemAppHeaderProps = { onBack?: () => void };

export function SystemAppHeader({ onBack }: SystemAppHeaderProps) {
  return (
    <AppHeader
      backIcon={Undo2}
      compact={Boolean(onBack)}
      layout={onBack ? 'centered' : 'split'}
      logo={<Image resizeMode="contain" source={logo} style={styles.logo} />}
      onBack={onBack}
      right={<ProfileAvatar />}
    />
  );
}

function ProfileAvatar() {
  return (
    <View
      accessibilityLabel={`Perfil de ${homeOverviewMock.user.name}`}
      accessibilityRole="image"
      style={styles.avatarFrame}
    >
      <View style={styles.avatar}>
        <AppText style={styles.avatarText} tone="accent">
          {homeOverviewMock.user.initial}
        </AppText>
      </View>
      <View style={styles.notificationDot} />
    </View>
  );
}

const styles = StyleSheet.create({
  logo: { width: 143, height: 30 },
  avatarFrame: { width: 30, height: 30 },
  avatar: {
    width: 30,
    height: 30,
    alignItems: 'center',
    justifyContent: 'center',
    overflow: 'hidden',
    borderWidth: 0.8,
    borderColor: colors.white,
    borderRadius: radii.full,
    backgroundColor: 'rgba(26, 169, 155, 0.25)',
  },
  avatarText: { fontSize: 14, lineHeight: 24 },
  notificationDot: {
    position: 'absolute',
    top: 0,
    right: -2,
    width: 8,
    height: 8,
    borderWidth: 0.8,
    borderColor: colors.white,
    borderRadius: radii.full,
    backgroundColor: colors.accent,
  },
});
