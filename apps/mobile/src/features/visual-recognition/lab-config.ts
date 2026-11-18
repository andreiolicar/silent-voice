import { Platform } from 'react-native';
import { isIosLabEnabled } from './capture-diagnostics';

export const iosLabEnabled = isIosLabEnabled(
  Platform.OS,
  process.env.EXPO_PUBLIC_ENABLE_IOS_LAB,
);
