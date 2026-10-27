import {
  deviceConnectionStates,
  type DeviceConnectionState,
} from '@/domain/device';

type ConnectionStateCopy = {
  description: string;
  moduleStatus: string;
  title: string;
  tone: 'error' | 'neutral' | 'success';
};

export const mockUsbConnectionSequence = [
  'waitingForUsb',
  'detected',
  'authorizationRequired',
  'connecting',
  'connected',
] as const satisfies readonly DeviceConnectionState[];

export const connectionStateCopy: Record<
  DeviceConnectionState,
  ConnectionStateCopy
> = {
  disconnected: {
    title: 'Desconectado',
    description: 'Prepare o módulo para iniciar a conexão por cabo.',
    moduleStatus: 'Desconectado',
    tone: 'neutral',
  },
  waitingForUsb: {
    title: 'Aguardando cabo',
    description: 'Conecte o cabo de dados USB ao celular.',
    moduleStatus: 'Aguardando conexão',
    tone: 'neutral',
  },
  detected: {
    title: 'Dispositivo detectado',
    description: 'O Módulo Silent Voice foi encontrado.',
    moduleStatus: 'Detectado',
    tone: 'success',
  },
  authorizationRequired: {
    title: 'Aguardando autorização',
    description: 'Confirme o acesso quando o sistema solicitar.',
    moduleStatus: 'Aguardando autorização',
    tone: 'neutral',
  },
  connecting: {
    title: 'Conectando',
    description: 'Preparando a conexão USB com o módulo.',
    moduleStatus: 'Conectando',
    tone: 'neutral',
  },
  connected: {
    title: 'Conectado',
    description: 'Módulo Silent Voice conectado por USB.',
    moduleStatus: 'Conectado por USB',
    tone: 'success',
  },
  failed: {
    title: 'Falha na conexão',
    description: 'Verifique o cabo de dados e tente novamente.',
    moduleStatus: 'Não conectado',
    tone: 'error',
  },
};

export function resolveMockConnectionState(
  value: string | string[] | undefined,
) {
  const state = Array.isArray(value) ? value[0] : value;
  return deviceConnectionStates.find((candidate) => candidate === state);
}
