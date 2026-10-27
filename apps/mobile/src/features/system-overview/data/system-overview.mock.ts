export type SystemMetricId = 'power' | 'connection' | 'latency' | 'modules';

export type SystemModuleId =
  'raspberryPi' | 'esp32' | 'myoware' | 'camera' | 'inmp441' | 'audioOutput';

export type SystemModule = Readonly<{
  detail: string;
  icon: 'activity' | 'camera' | 'gateway' | 'mic' | 'processor' | 'speaker';
  id: SystemModuleId;
  name: string;
  requirement: 'required';
  state: 'connected' | 'disconnected';
}>;

export type SystemMetric = Readonly<{
  description: string;
  id: SystemMetricId;
  label: string;
  value: string;
}>;

export type HomeOverview = Readonly<{
  communication: Readonly<{
    description: string;
    title: string;
  }>;
  metrics: readonly SystemMetric[];
  status: Readonly<{
    description: string;
    title: string;
  }>;
  user: Readonly<{
    initial: string;
    name: string;
    welcome: string;
  }>;
}>;

export type HealthMetricId = 'power' | 'latency' | 'processor' | 'temperature';

export type HealthMetricValue =
  | Readonly<{ state: 'available'; text: string }>
  | Readonly<{ state: 'unknown' | 'unavailable' }>;

export type HealthMetric = Readonly<{
  description?: string;
  icon: 'activity' | 'cpu' | 'power' | 'thermometer';
  id: HealthMetricId;
  label: string;
  progress?: number;
  status?: string;
  value: HealthMetricValue;
}>;

export type SystemHealth = Readonly<{
  metrics: readonly HealthMetric[];
  privacy: string;
  stability: Readonly<{
    description: string;
    status: string;
    title: string;
  }>;
}>;

export const systemModulesMock = [
  {
    id: 'raspberryPi',
    name: 'Raspberry Pi Zero 2 W',
    icon: 'gateway',
    detail: 'Gateway principal • USB',
    requirement: 'required',
    state: 'connected',
  },
  {
    id: 'esp32',
    name: 'ESP32-S3',
    icon: 'processor',
    detail: 'Aquisição EMG • UART',
    requirement: 'required',
    state: 'connected',
  },
  {
    id: 'myoware',
    name: 'MyoWare 2',
    icon: 'activity',
    detail: 'Sinal neuromuscular',
    requirement: 'required',
    state: 'connected',
  },
  {
    id: 'camera',
    name: 'Câmera OV5647',
    icon: 'camera',
    detail: 'Visão • CSI',
    requirement: 'required',
    state: 'connected',
  },
  {
    id: 'inmp441',
    name: 'INMP441',
    icon: 'mic',
    detail: 'Contexto sonoro • I²S',
    requirement: 'required',
    state: 'connected',
  },
  {
    id: 'audioOutput',
    name: 'Saída de áudio',
    icon: 'speaker',
    detail: 'MAX98357A + alto-falante',
    requirement: 'required',
    state: 'connected',
  },
] as const satisfies readonly SystemModule[];

const requiredModules = systemModulesMock.filter(
  (module) => module.requirement === 'required',
);

export const requiredModuleSummary = {
  connected: requiredModules.filter((module) => module.state === 'connected')
    .length,
  total: requiredModules.length,
} as const;

export const homeOverviewMock: HomeOverview = {
  user: { initial: 'A', name: 'Andrei', welcome: 'Seja bem-vindo' },
  status: {
    title: 'Tudo operacional',
    description: 'Seu sistema está funcionando\nnormalmente.',
  },
  metrics: [
    {
      id: 'power',
      label: 'Alimentação',
      value: 'Estável',
      description: 'Módulo principal',
    },
    {
      id: 'latency',
      label: 'Latência',
      value: '142 ms',
      description: 'Tempo',
    },
    {
      id: 'connection',
      label: 'Conexão',
      value: 'USB',
      description: 'Conectado',
    },
    {
      id: 'modules',
      label: 'Módulos',
      value: `${requiredModuleSummary.connected}/${requiredModuleSummary.total}`,
      description: 'Operando',
    },
  ],
  communication: {
    title: 'Pronto para comunicação\nem tempo real',
    description:
      'Todos os sistemas estão ativos e\notimizados para uma comunicação\nclara e contínua.',
  },
};

export const systemHealthMock: SystemHealth = {
  metrics: [
    {
      id: 'power',
      icon: 'power',
      label: 'Alimentação',
      value: { state: 'available', text: 'Estável' },
      description: 'Fontes dedicadas operando.',
    },
    {
      id: 'temperature',
      icon: 'thermometer',
      label: 'Temperatura',
      value: { state: 'available', text: '47°C' },
      progress: 0.47,
      description: 'Raspberry Pi em faixa normal.',
    },
    {
      id: 'latency',
      icon: 'activity',
      label: 'Latência',
      value: { state: 'available', text: '142ms' },
      status: 'Abaixo de 200ms',
    },
    {
      id: 'processor',
      icon: 'cpu',
      label: 'Uso Raspberry Pi',
      value: { state: 'available', text: '48%' },
      progress: 0.48,
      description: 'Carga estimada do gateway.',
    },
  ],
  stability: {
    title: 'Estabilidade',
    description: 'Desempenho na última hora.',
    status: 'Estável',
  },
  privacy: 'Telemetria demonstrativa até a integração com o hardware.',
};
