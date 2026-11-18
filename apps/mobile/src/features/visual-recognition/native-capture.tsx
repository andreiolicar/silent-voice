import { requireNativeView, requireOptionalNativeModule } from 'expo';
import type { Ref } from 'react';
import type { ViewProps } from 'react-native';
import type { CapturedFrame } from './contract';
import type {
  CameraPermission,
  NativeCaptureReport,
  SyntheticNormalizationReport,
} from './capture-diagnostics';
import { iosLabEnabled } from './lab-config';

type CaptureModule = {
  getPermission(): Promise<CameraPermission>;
  requestPermission(): Promise<CameraPermission>;
  syntheticFrames(): Promise<CapturedFrame[]>;
  syntheticNormalization(): Promise<SyntheticNormalizationReport>;
};

export type CaptureViewHandle = {
  capture(): Promise<NativeCaptureReport>;
  captureNormalized(): Promise<NativeCaptureReport>;
  cancel(): Promise<void>;
};

export const nativeCapture = iosLabEnabled
  ? requireOptionalNativeModule<CaptureModule>('SilentVoiceCapture')
  : null;

export const CapturePreview = nativeCapture
  ? requireNativeView<ViewProps & { ref?: Ref<CaptureViewHandle> }>(
      'SilentVoiceCapture',
    )
  : null;
