export const deviceTransports = ['usb'] as const;

export type DeviceTransport = (typeof deviceTransports)[number];

export const deviceConnectionStates = [
  'disconnected',
  'waitingForUsb',
  'detected',
  'authorizationRequired',
  'connecting',
  'connected',
  'failed',
] as const;

export type DeviceConnectionState = (typeof deviceConnectionStates)[number];

export const sessionStates = [
  'idle',
  'ready',
  'capturing',
  'decoding',
  'candidate',
  'validating',
  'confirmed',
  'speaking',
  'needsRetry',
  'error',
] as const;

export type SessionState = (typeof sessionStates)[number];
