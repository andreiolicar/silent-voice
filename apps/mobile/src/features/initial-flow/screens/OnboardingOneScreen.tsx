import {
  BrainCircuit,
  ChartNoAxesCombined,
  SlidersVertical,
  type LucideIcon,
} from 'lucide-react-native';
import { useRouter } from 'expo-router';
import { Image, Platform, StyleSheet, View } from 'react-native';

import { AppText, Card } from '@/components/ui';
import {
  BrandLogo,
  InitialFlowScreen,
  OnboardingFooter,
} from '@/features/initial-flow/components';
import { colors, fontFamilies, radii } from '@/theme';

const hero = require('@/assets/images/initial-flow/onboarding-one-hero.png');
const background = require('@/assets/images/initial-flow/onboarding-one-background.png');
const decor = require('@/assets/images/initial-flow/onboarding-one-decor.png');

const features: {
  description: string;
  icon: LucideIcon;
  title: string;
}[] = [
  {
    title: 'Monitoramento',
    description: 'Acompanhe sinais e\nstatus dos módulos\nem tempo real.',
    icon: ChartNoAxesCombined,
  },
  {
    title: 'IA',
    description: 'Inteligência que\naprende e interpreta\nsuas ações.',
    icon: BrainCircuit,
  },
  {
    title: 'Personalização',
    description: 'Ajustes que se\nadaptam a você\ne à sua rotina.',
    icon: SlidersVertical,
  },
];

export default function OnboardingOne() {
  const router = useRouter();

  return (
    <InitialFlowScreen
      background={background}
      backgroundStyle={styles.background}
      contentStyle={styles.content}
    >
      <Image source={decor} style={styles.decor} />
      <BrandLogo style={styles.logo} />
      <View style={styles.intro}>
        <View style={styles.heading}>
          <AppText style={styles.title} variant="screenTitle">
            Seu centro de{`\n`}comando para{`\n`}comunicação assistiva
            <AppText style={styles.period} variant="screenTitle">
              .
            </AppText>
          </AppText>
          <AppText style={styles.subtitle} tone="secondary">
            Monitore módulos, acompanhe sinais em{`\n`}tempo real e personalize
            a inteligência{`\n`}do Silent Voice.
          </AppText>
        </View>
        <View style={styles.heroFrame}>
          <Image source={hero} style={styles.hero} />
        </View>
      </View>
      <View style={styles.features}>
        {features.map(({ description, icon: Icon, title }) => (
          <Card key={title} style={styles.featureCard}>
            <View style={styles.featureIcon}>
              <Icon color={colors.accent} size={28} />
            </View>
            <AppText style={styles.featureTitle} variant="caption">
              {title}
            </AppText>
            <AppText
              style={styles.featureDescription}
              tone="secondary"
              variant="caption"
            >
              {description}
            </AppText>
          </Card>
        ))}
      </View>
      <View style={styles.spacer} />
      <OnboardingFooter
        currentPage={1}
        onContinue={() => router.push('/onboarding/2')}
        onSkip={() => router.replace('/permissions')}
      />
    </InitialFlowScreen>
  );
}

const styles = StyleSheet.create({
  background: { top: 80, bottom: undefined, height: 714 },
  decor: {
    position: 'absolute',
    top: 378,
    left: 5,
    width: 392,
    height: 50,
  },
  content: {
    paddingTop: Platform.select({ web: 75, default: 18 }),
    paddingBottom: 29,
  },
  logo: { alignSelf: 'center', marginBottom: 35 },
  intro: { position: 'relative', height: 387 },
  heading: { position: 'relative', zIndex: 1 },
  title: {
    fontSize: 26,
    lineHeight: 28,
    letterSpacing: -0.4,
    textAlign: 'left',
  },
  period: { color: colors.accent, fontSize: 26, lineHeight: 28 },
  subtitle: {
    marginTop: 10,
    fontFamily: fontFamilies.regular,
    fontSize: 12,
    lineHeight: 16,
  },
  heroFrame: {
    position: 'absolute',
    top: 128,
    width: '100%',
    height: 259,
    overflow: 'hidden',
  },
  hero: {
    position: 'absolute',
    top: -28,
    left: -72,
    width: 498,
    height: 331,
  },
  features: {
    height: 128,
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 35,
  },
  featureCard: {
    width: 98,
    height: 128,
    alignItems: 'center',
    padding: 12,
  },
  featureIcon: {
    width: 48,
    height: 48,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: radii.full,
    backgroundColor: colors.background,
  },
  featureTitle: {
    fontFamily: fontFamilies.semiBold,
    fontSize: 10,
    lineHeight: 25,
    textAlign: 'center',
  },
  featureDescription: {
    fontSize: 7,
    lineHeight: 10,
    textAlign: 'center',
  },
  spacer: { flexGrow: 1, minHeight: 20 },
});
