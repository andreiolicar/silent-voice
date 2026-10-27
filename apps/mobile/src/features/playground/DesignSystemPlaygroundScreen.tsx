import { ArrowRight, Camera, Radio, Usb, User, Zap } from 'lucide-react-native';
import { useState, type PropsWithChildren } from 'react';
import { StyleSheet, View } from 'react-native';

import {
  AppHeader,
  BottomNavigation,
  type BottomNavigationItem,
  Screen,
  ScreenHeading,
} from '@/components/layout';
import {
  DeviceCard,
  MetricCard,
  ModuleCard,
  PrivacyNotice,
  RadarIndicator,
  StatusBadge,
} from '@/components/silent-voice';
import {
  AppText,
  Badge,
  Button,
  Card,
  IconButton,
  Toggle,
} from '@/components/ui';
import { spacing } from '@/theme';

export default function DesignSystemPlayground() {
  const [toggleEnabled, setToggleEnabled] = useState(true);
  const [activeItem, setActiveItem] = useState<BottomNavigationItem>('home');

  return (
    <Screen contentStyle={styles.screen} scroll>
      <View style={styles.content}>
        <AppHeader
          logo={<AppText variant="label">SILENT VOICE</AppText>}
          onBack={() => undefined}
          right={
            <IconButton
              accessibilityLabel="Perfil de demonstração"
              icon={User}
              variant="surface"
            />
          }
        />

        <ScreenHeading
          subtitle="Componentes reutilizáveis — não representa uma tela final."
          title="Design System"
        />

        <PlaygroundSection title="Tipografia">
          <AppText variant="screenTitle">Título de tela</AppText>
          <AppText variant="sectionTitle">Título de seção</AppText>
          <AppText variant="body">Texto principal legível em Manrope.</AppText>
          <AppText tone="secondary" variant="caption">
            Informação auxiliar normalizada para 11 px.
          </AppText>
        </PlaygroundSection>

        <PlaygroundSection title="Ações">
          <View style={styles.row}>
            <Button label="Continuar" rightIcon={ArrowRight} />
            <Button label="Agora não" variant="ghost" />
            <Button label="Carregando" loading />
            <Button disabled label="Indisponível" />
          </View>
        </PlaygroundSection>

        <PlaygroundSection title="Badges e controle">
          <View style={styles.row}>
            <Badge tone="success">Conectado</Badge>
            <Badge>Opcional</Badge>
            <Badge tone="warning">Atenção</Badge>
            <Badge tone="error">Falha</Badge>
          </View>
          <Card style={styles.toggleRow}>
            <View style={styles.flex}>
              <AppText variant="cardTitle">Validação contextual</AppText>
              <AppText tone="secondary" variant="caption">
                Exemplo interativo do controle base
              </AppText>
            </View>
            <Toggle
              accessibilityLabel="Ativar validação contextual"
              onValueChange={setToggleEnabled}
              value={toggleEnabled}
            />
          </Card>
        </PlaygroundSection>

        <PlaygroundSection title="Indicadores Silent Voice">
          <View style={styles.centered}>
            <RadarIndicator
              accessibilityLabel="Sistema pronto para comunicação"
              icon={Radio}
            />
            <StatusBadge label="Sistema estável" />
            <PrivacyNotice text="Seus dados permanecem sob seu controle." />
          </View>
        </PlaygroundSection>

        <PlaygroundSection title="Métricas">
          <View style={styles.cardGrid}>
            <MetricCard
              description="Módulo principal"
              icon={Zap}
              label="Alimentação"
              value="Estável"
            />
            <MetricCard
              description="Resposta estimada"
              icon={Radio}
              label="Latência"
              value="128ms"
            />
          </View>
        </PlaygroundSection>

        <View style={styles.section}>
          <View style={styles.devicesHeadline}>
            <AppText
              style={styles.devicesHeadlineLabel}
              tone="secondary"
              variant="caption"
            >
              CONEXÃO USB
            </AppText>
          </View>
          <DeviceCard
            description="Raspberry Pi Zero 2 W"
            icon={Usb}
            name="Módulo Silent Voice"
            status="Conectado por USB"
            statusTone="success"
          />
        </View>

        <PlaygroundSection title="Módulos">
          <ModuleCard
            detail="Visão • CSI"
            icon={Camera}
            name="Câmera OV5647"
            requirement="required"
            state="connected"
          />
        </PlaygroundSection>

        <PlaygroundSection title="Navegação inferior">
          <BottomNavigation
            activeItem={activeItem}
            onItemPress={setActiveItem}
          />
        </PlaygroundSection>
      </View>
    </Screen>
  );
}

function PlaygroundSection({
  children,
  title,
}: PropsWithChildren<{ title: string }>) {
  return (
    <View style={styles.section}>
      <AppText variant="sectionTitle">{title}</AppText>
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { paddingBottom: spacing.section },
  content: {
    width: '100%',
    maxWidth: 720,
    alignSelf: 'center',
    gap: spacing.section,
  },
  section: { gap: spacing.md },
  row: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    alignItems: 'center',
    gap: spacing.sm,
  },
  cardGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.md },
  devicesHeadline: {
    minHeight: 24,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  devicesHeadlineLabel: { letterSpacing: 1 },
  toggleRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.md },
  flex: { flex: 1, gap: spacing.xxs },
  centered: { alignItems: 'center', gap: spacing.md },
});
