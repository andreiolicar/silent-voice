import { create } from 'zustand';

import type { DeviceConnectionState } from '@/domain/device';

type DeviceStore = {
  connectionState: DeviceConnectionState;
  setConnectionState: (connectionState: DeviceConnectionState) => void;
};

export const useDeviceStore = create<DeviceStore>((set) => ({
  connectionState: 'disconnected',
  setConnectionState: (connectionState) => set({ connectionState }),
}));
