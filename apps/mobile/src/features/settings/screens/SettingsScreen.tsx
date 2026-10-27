import {
  Accessibility,
  Bell,
  KeyRound,
  LockKeyhole,
  ShieldCheck,
  UserRound,
  Volume2,
  type LucideIcon,
} from 'lucide-react-native';
import { useState } from 'react';
import { StyleSheet, View } from 'react-native';

import { ScreenHeading } from '@/components/layout';
import { AppText, Card } from '@/components/ui';
import { MainAppScreen } from '@/features/system-overview/components/MainAppScreen';
import { SystemAppHeader } from '@/features/system-overview/components/SystemAppHeader';
import { spacing } from '@/theme';

import { SettingsItem } from '../components/SettingsItem';
import {
  settingsSectionsMock,
  type SettingsItemId,
} from '../data/settings.mock';

const settingIcons: Record<SettingsItemId, LucideIcon> = {
  profile: UserRound,
  security: ShieldCheck,
  notifications: Bell,
  accessibility: Accessibility,
  voicePreferences: Volume2,
  privacy: LockKeyhole,
  permissions: KeyRound,
};

export default function SettingsScreen() {
  const [notificationsEnabled, setNotificationsEnabled] = useState(true);

  return (
    <MainAppScreen activeItem="settings">
      <SystemAppHeader />

      <View style={styles.heading}>
        <ScreenHeading
          subtitle="Personalize sua experiência."
          title="Ajustes"
        />
      </View>

      <View style={styles.section}>
        {settingsSectionsMock.map((section) => (
          <View key={section.id} style={styles.group}>
            <AppText variant="cardTitle">{section.title}</AppText>
            <Card padding="none">
              {section.items.map((item, index) => (
                <SettingsItem
                  description={item.description}
                  icon={settingIcons[item.id]}
                  key={item.id}
                  onValueChange={
                    item.id === 'notifications'
                      ? setNotificationsEnabled
                      : undefined
                  }
                  showDivider={index > 0}
                  title={item.title}
                  type={item.kind}
                  value={
                    item.id === 'notifications'
                      ? notificationsEnabled
                      : undefined
                  }
                />
              ))}
            </Card>
          </View>
        ))}
      </View>
    </MainAppScreen>
  );
}

const styles = StyleSheet.create({
  heading: { marginTop: spacing.section },
  section: { gap: spacing.lg, marginTop: spacing.section },
  group: { gap: spacing.sm },
});
