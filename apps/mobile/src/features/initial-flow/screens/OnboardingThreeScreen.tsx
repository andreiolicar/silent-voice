import { Check } from 'lucide-react-native';
import { useRouter } from 'expo-router';
import { Image, Platform, StyleSheet, View } from 'react-native';

import { AppText } from '@/components/ui';
import {
  BrandLogo,
  InitialFlowScreen,
  OnboardingFooter,
} from '@/features/initial-flow/components';
import { colors, fontFamilies, radii } from '@/theme';

const shield = require('@/assets/images/initial-flow/onboarding-three-shield.png');
const background = require('@/assets/images/initial-flow/onboarding-three-background.png');
const waves = require('@/assets/images/initial-flow/onboarding-three-waves.png');

const guarantees = [
  'Processamento local e offline.',
  'Comunicação direta por cabo.',
  'Seus dados permanecem sob seu controle.',
];

export default function OnboardingThree() {
  const router = useRouter();

  return (
    <InitialFlowScreen
      background={background}
      backgroundStyle={styles.background}
      contentStyle={styles.content}
    >
      <Image source={waves} style={styles.waves} />
      <BrandLogo style={styles.logo} />
      <View style={styles.heading}>
        <AppText style={styles.title} variant="screenTitle">
          Privacidade e{`\n`}segurança em{`\n`}primeiro lugar
          <AppText style={styles.period} variant="screenTitle">
            .
          </AppText>
        </AppText>
        <AppText style={styles.subtitle} tone="secondary">
          A interpretação acontece no celular,{`\n`}sem depender de serviços em
          nuvem.
        </AppText>
      </View>

      <View style={styles.shieldFrame}>
        <Image resizeMode="contain" source={shield} style={styles.shield} />
      </View>

      <View style={styles.guarantees}>
        {guarantees.map((guarantee) => (
          <View key={guarantee} style={styles.guarantee}>
            <View style={styles.check}>
              <Check color={colors.white} size={12} strokeWidth={2.5} />
            </View>
            <AppText style={styles.guaranteeText} tone="secondary">
              {guarantee}
            </AppText>
          </View>
        ))}
      </View>

      <View style={styles.spacer} />
      <OnboardingFooter
        currentPage={3}
        onContinue={() => router.push('/permissions')}
        onSkip={() => router.replace('/permissions')}
      />
    </InitialFlowScreen>
  );
}

const styles = StyleSheet.create({
  background: { top: 114, bottom: undefined, height: 714 },
  waves: {
    position: 'absolute',
    top: 420,
    left: 0,
    width: 402,
    height: 51,
  },
  content: {
    paddingTop: Platform.select({ web: 75, default: 18 }),
    paddingBottom: 29,
  },
  logo: { alignSelf: 'center', marginBottom: 35 },
  heading: { alignItems: 'center', gap: 10 },
  title: {
    fontSize: 26,
    lineHeight: 28,
    letterSpacing: -0.4,
    textAlign: 'center',
  },
  period: { color: colors.accent, fontSize: 26, lineHeight: 28 },
  subtitle: {
    fontFamily: fontFamilies.regular,
    fontSize: 12,
    lineHeight: 16,
    textAlign: 'center',
  },
  shieldFrame: {
    width: 188.5,
    height: 220.325,
    alignSelf: 'center',
    marginTop: 35,
  },
  shield: {
    position: 'absolute',
    top: -10,
    left: -10,
    width: 208.5,
    height: 240.325,
  },
  guarantees: { alignSelf: 'center', gap: 16, marginTop: 40 },
  guarantee: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  check: {
    width: 18,
    height: 18,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: radii.full,
    backgroundColor: colors.accent,
  },
  guaranteeText: {
    fontFamily: fontFamilies.medium,
    fontSize: 10,
    lineHeight: 18,
  },
  spacer: { flexGrow: 1, minHeight: 20 },
});
