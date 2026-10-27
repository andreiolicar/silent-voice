export type HubResourceId =
  'calibration' | 'modules' | 'systemHealth' | 'connectivity';

export type HubResource = {
  description: string;
  id: HubResourceId;
  title: string;
};

export const hubDeviceMock = {
  connected: true,
  gateway: 'Raspberry Pi Zero 2 W',
  name: 'Módulo Silent Voice',
  transport: 'USB',
} as const;

export const hubResourcesMock: HubResource[] = [
  {
    id: 'calibration',
    title: 'Calibração',
    description: 'Ajuste a leitura dos seus sinais.',
  },
  {
    id: 'modules',
    title: 'Status dos módulos',
    description: 'Confira conexão e integridade.',
  },
  {
    id: 'systemHealth',
    title: 'Saúde do sistema',
    description: 'Acompanhe o desempenho do hardware.',
  },
  {
    id: 'connectivity',
    title: 'Conectividade',
    description: 'Gerencie a conexão USB com o módulo.',
  },
];
