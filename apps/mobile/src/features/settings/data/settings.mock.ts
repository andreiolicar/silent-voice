export type SettingsItemId =
  | 'profile'
  | 'security'
  | 'notifications'
  | 'accessibility'
  | 'voicePreferences'
  | 'privacy'
  | 'permissions';

export type SettingsItemData = {
  description?: string;
  id: SettingsItemId;
  kind: 'navigation' | 'toggle';
  title: string;
};

export type SettingsSectionData = {
  id: 'account' | 'application' | 'privacy';
  items: SettingsItemData[];
  title: string;
};

export const settingsSectionsMock: SettingsSectionData[] = [
  {
    id: 'account',
    title: 'Conta',
    items: [
      { id: 'profile', title: 'Perfil', kind: 'navigation' },
      { id: 'security', title: 'Segurança', kind: 'navigation' },
    ],
  },
  {
    id: 'application',
    title: 'Aplicativo',
    items: [
      {
        id: 'notifications',
        title: 'Notificações',
        description: 'Avisos importantes do aplicativo.',
        kind: 'toggle',
      },
      { id: 'accessibility', title: 'Acessibilidade', kind: 'navigation' },
      {
        id: 'voicePreferences',
        title: 'Preferências de voz',
        kind: 'navigation',
      },
    ],
  },
  {
    id: 'privacy',
    title: 'Privacidade',
    items: [
      { id: 'privacy', title: 'Privacidade e dados', kind: 'navigation' },
      { id: 'permissions', title: 'Permissões', kind: 'navigation' },
    ],
  },
];
