import {
  Activity,
  Camera,
  Cpu,
  Mic,
  Server,
  Volume2,
  type LucideIcon,
} from 'lucide-react-native';
import { useRouter } from 'expo-router';
import { StyleSheet, View } from 'react-native';

import { ModuleCard } from '@/components/silent-voice';
import { AppText } from '@/components/ui';
import { fontFamilies, spacing } from '@/theme';

import { LiveCommunicationButton } from '../components/LiveCommunicationButton';
import { MainAppScreen } from '../components/MainAppScreen';
import { SystemAppHeader } from '../components/SystemAppHeader';
import {
  systemModulesMock,
  type SystemModule,
} from '../data/system-overview.mock';

const moduleIcons: Record<SystemModule['icon'], LucideIcon> = {
  activity: Activity,
  camera: Camera,
  gateway: Server,
  mic: Mic,
  processor: Cpu,
  speaker: Volume2,
};

export default function ModulesScreen() {
  const router = useRouter();

  return (
    <MainAppScreen>
      <SystemAppHeader onBack={() => router.replace('/home')} />

      <View style={styles.heading}>
        <AppText style={styles.title}>Status dos módulos</AppText>
        <AppText style={styles.subtitle} tone="secondary">
          Integridade e conexão.
        </AppText>
      </View>

      <View style={styles.section}>
        {systemModulesMock.map((module) => (
          <ModuleCard
            detail={module.detail}
            icon={moduleIcons[module.icon]}
            iconSize={module.icon === 'camera' ? 26 : 24}
            key={module.id}
            name={module.name}
            requirement={module.requirement}
            state={module.state}
          />
        ))}
        <LiveCommunicationButton onPress={() => router.push('/live')} />
      </View>
    </MainAppScreen>
  );
}

const styles = StyleSheet.create({
  heading: { gap: spacing.sm, marginTop: spacing.section },
  title: {
    fontFamily: fontFamilies.bold,
    fontSize: 26,
    lineHeight: 28,
    letterSpacing: -0.4,
  },
  subtitle: { fontSize: 12, lineHeight: 16 },
  section: { gap: spacing.md, marginTop: spacing.section },
});
