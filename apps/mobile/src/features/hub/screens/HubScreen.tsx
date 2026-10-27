import { Activity, Cable, Cpu, SlidersHorizontal } from 'lucide-react-native';
import { useRouter } from 'expo-router';
import { StyleSheet, View } from 'react-native';

import { ScreenHeading } from '@/components/layout';
import { AppText } from '@/components/ui';
import { spacing } from '@/theme';
import { MainAppScreen } from '@/features/system-overview/components/MainAppScreen';
import { SystemAppHeader } from '@/features/system-overview/components/SystemAppHeader';

import { HubDeviceCard } from '../components/HubDeviceCard';
import { HubResourceItem } from '../components/HubResourceItem';
import {
  hubDeviceMock,
  hubResourcesMock,
  type HubResourceId,
} from '../data/hub.mock';

const resourceIcons = {
  calibration: SlidersHorizontal,
  modules: Cpu,
  systemHealth: Activity,
  connectivity: Cable,
} as const;

export default function HubScreen() {
  const router = useRouter();

  const resourceActions: Partial<Record<HubResourceId, () => void>> = {
    calibration: () => router.push('/calibration?origin=hub'),
    modules: () => router.push('/modules'),
    systemHealth: () => router.push('/system-health'),
    connectivity: () => router.push('/connection'),
  };

  return (
    <MainAppScreen activeItem="hub">
      <SystemAppHeader />

      <View style={styles.heading}>
        <ScreenHeading
          subtitle="Gerencie seu dispositivo e recursos."
          title="Hub"
        />
      </View>

      <View style={styles.section}>
        <HubDeviceCard {...hubDeviceMock} />

        <View style={styles.resources}>
          <AppText variant="cardTitle">Recursos</AppText>
          <View style={styles.resourceList}>
            {hubResourcesMock.map((resource) => (
              <HubResourceItem
                description={resource.description}
                icon={resourceIcons[resource.id]}
                key={resource.id}
                onPress={resourceActions[resource.id]}
                title={resource.title}
              />
            ))}
          </View>
        </View>
      </View>
    </MainAppScreen>
  );
}

const styles = StyleSheet.create({
  heading: { marginTop: spacing.section },
  section: { gap: spacing.xl, marginTop: spacing.section },
  resources: { gap: spacing.md },
  resourceList: { gap: spacing.sm },
});
