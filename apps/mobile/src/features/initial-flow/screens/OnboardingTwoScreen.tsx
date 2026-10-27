import {
  ShieldCheck,
  Workflow,
  Zap,
  type LucideIcon,
} from 'lucide-react-native';
import { useRouter } from 'expo-router';
import { Image, Platform, StyleSheet, View } from 'react-native';

import { AppText } from '@/components/ui';
import {
  BrandLogo,
  InitialFlowScreen,
  OnboardingFooter,
} from '@/features/initial-flow/components';
import { colors, fontFamilies, radii } from '@/theme';

const bodyImage = require('@/assets/images/initial-flow/onboarding-two-body.png');
const aiImage = require('@/assets/images/initial-flow/onboarding-two-ai.png');
const voiceImage = require('@/assets/images/initial-flow/onboarding-two-voice.png');
const arrowImage = require('@/assets/images/initial-flow/onboarding-two-arrow.png');

const steps = [
  { label: 'Corpo', caption: 'Intenção', source: bodyImage },
  { label: 'IA', caption: 'Decodifica e valida', source: aiImage },
  { label: 'Voz', caption: 'Respostas em tempo real', source: voiceImage },
];

const benefits: {
  description: string;
  icon: LucideIcon;
  title: string;
}[] = [
  {
    icon: Zap,
    title: 'Resposta instantânea',
    description: 'Interações em tempo real para decisões e ações imediatas.',
  },
  {
    icon: Workflow,
    title: 'Integração inteligente',
    description: 'Seus módulos IoT conectados e respondendo sem atrasos.',
  },
  {
    icon: ShieldCheck,
    title: 'Confiável e estável',
    description: 'Comunicação segura e contínua em qualquer ambiente.',
  },
];

export default function OnboardingTwo() {
  const router = useRouter();

  return (
    <InitialFlowScreen background={null} contentStyle={styles.content}>
      <BrandLogo style={styles.logo} />
      <View style={styles.heading}>
        <AppText style={styles.title} variant="screenTitle">
          Comunicação{`\n`}em tempo real
          <AppText style={styles.period} variant="screenTitle">
            .
          </AppText>
        </AppText>
        <AppText style={styles.subtitle} tone="secondary">
          Validação da fala decodificada e controle{`\n`}dos módulos IoT em uma
          experiência fluída.
        </AppText>
      </View>

      <View style={styles.pipeline}>
        <View style={styles.concentricRings} pointerEvents="none">
          {[132, 118, 104, 90].map((size, index) => (
            <View
              key={size}
              style={[
                styles.ring,
                { width: size, height: size, opacity: 0.2 + index * 0.1 },
                index === 3 && styles.ringDashed,
              ]}
            />
          ))}
        </View>
        <Image source={arrowImage} style={[styles.arrow, styles.arrowOne]} />
        <Image source={arrowImage} style={[styles.arrow, styles.arrowTwo]} />
        {steps.map((step, index) => (
          <View key={step.label} style={styles.pipelineItem}>
            <View style={styles.visualCircle}>
              <Image
                resizeMode="contain"
                source={step.source}
                style={[
                  styles.visualImage,
                  index === 1 && styles.aiImage,
                  index === 2 && styles.voiceImage,
                ]}
              />
            </View>
            <View style={styles.stepText}>
              <AppText style={styles.stepLabel}>{step.label}</AppText>
              <AppText style={styles.stepCaption} tone="secondary">
                {step.caption}
              </AppText>
            </View>
          </View>
        ))}
      </View>

      <View style={styles.benefits}>
        {benefits.map(({ description, icon: Icon, title }, index) => (
          <View key={title}>
            {index > 0 ? <View style={styles.divider} /> : null}
            <View style={styles.benefit}>
              <View style={styles.benefitIcon}>
                <Icon color={colors.accent} size={22} strokeWidth={1.5} />
              </View>
              <View style={styles.benefitText}>
                <AppText style={styles.benefitTitle}>{title}</AppText>
                <AppText style={styles.benefitDescription} tone="secondary">
                  {description}
                </AppText>
              </View>
            </View>
          </View>
        ))}
      </View>

      <View style={styles.spacer} />
      <OnboardingFooter
        currentPage={2}
        onContinue={() => router.push('/onboarding/3')}
        onSkip={() => router.replace('/permissions')}
      />
    </InitialFlowScreen>
  );
}

const styles = StyleSheet.create({
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
  pipeline: {
    position: 'relative',
    height: 128,
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 35,
  },
  pipelineItem: { width: 86, alignItems: 'center' },
  visualCircle: {
    width: 84,
    height: 84,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: radii.full,
    backgroundColor: colors.surface,
    overflow: 'hidden',
  },
  visualImage: { width: 44, height: 44 },
  aiImage: { width: 94, height: 94 },
  voiceImage: { width: 73, height: 73 },
  concentricRings: {
    position: 'absolute',
    top: -24,
    left: 105,
    width: 132,
    height: 132,
    alignItems: 'center',
    justifyContent: 'center',
  },
  ring: {
    position: 'absolute',
    borderWidth: 0.5,
    borderColor: 'rgba(26, 169, 155, 0.2)',
    borderRadius: radii.full,
  },
  ringDashed: { borderStyle: 'dashed' },
  arrow: { position: 'absolute', top: 38, width: 25, height: 8 },
  arrowOne: { left: 94 },
  arrowTwo: { left: 222 },
  stepText: { alignItems: 'center', marginTop: 16, gap: 6 },
  stepLabel: {
    width: 86,
    fontFamily: fontFamilies.semiBold,
    fontSize: 10,
    lineHeight: 10,
    textAlign: 'center',
  },
  stepCaption: {
    fontFamily: fontFamilies.medium,
    fontSize: 7,
    lineHeight: 10,
    textAlign: 'center',
  },
  benefits: { marginTop: 50 },
  benefit: {
    height: 22,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 16,
  },
  benefitIcon: {
    width: 22,
    height: 22,
    alignItems: 'center',
    justifyContent: 'center',
  },
  benefitText: { height: 22, justifyContent: 'space-between' },
  benefitTitle: {
    fontFamily: fontFamilies.semiBold,
    fontSize: 9,
    lineHeight: 10,
  },
  benefitDescription: {
    fontFamily: fontFamilies.medium,
    fontSize: 7,
    lineHeight: 8,
  },
  divider: {
    height: 1,
    marginVertical: 20,
    backgroundColor: colors.border,
  },
  spacer: { flexGrow: 1, minHeight: 20 },
});
