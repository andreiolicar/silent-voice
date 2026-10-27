export const calibrationSteps = [
  'preparation',
  'rest',
  'muscle',
  'visual',
  'validation',
  'complete',
] as const;

export type CalibrationStep = (typeof calibrationSteps)[number];

export const calibrationCaptureStates = [
  'idle',
  'waiting',
  'capturing',
  'processing',
  'success',
  'retry',
] as const;

export type CalibrationCaptureState = (typeof calibrationCaptureStates)[number];

export type CalibrationOrigin = 'hub' | 'setup';

export type CalibrationResultState = 'adequate' | 'captured' | 'pending';

export type CalibrationResult = {
  muscle: CalibrationResultState;
  rest: CalibrationResultState;
  visual: CalibrationResultState;
};
