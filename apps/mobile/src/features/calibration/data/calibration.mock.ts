import {
  calibrationCaptureStates,
  calibrationSteps,
  type CalibrationCaptureState,
  type CalibrationOrigin,
  type CalibrationResult,
  type CalibrationStep,
} from '@/domain/calibration';

export type CalibrationInspection = {
  state?: CalibrationCaptureState;
  step: CalibrationStep;
};

export type MockCalibrationTransition = {
  afterMs: number;
  state: CalibrationCaptureState;
};

export const calibrationOperationalSteps = [
  'preparation',
  'rest',
  'muscle',
  'visual',
  'validation',
] as const satisfies readonly CalibrationStep[];

export const initialCalibrationResult: CalibrationResult = {
  rest: 'pending',
  muscle: 'pending',
  visual: 'pending',
};

export const mockCalibrationSequences: Partial<
  Record<CalibrationStep, readonly MockCalibrationTransition[]>
> = {
  rest: [{ afterMs: 1400, state: 'success' }],
  muscle: [
    { afterMs: 700, state: 'capturing' },
    { afterMs: 1700, state: 'processing' },
    { afterMs: 2700, state: 'success' },
  ],
  visual: [{ afterMs: 1500, state: 'success' }],
  validation: [{ afterMs: 1200, state: 'success' }],
};

export const calibrationStateProgress: Record<CalibrationCaptureState, number> =
  {
    idle: 0,
    waiting: 0.12,
    capturing: 0.55,
    processing: 0.82,
    success: 1,
    retry: 0.35,
  };

export function getInitialCalibrationState(
  step: CalibrationStep,
): CalibrationCaptureState {
  const states: Record<CalibrationStep, CalibrationCaptureState> = {
    preparation: 'idle',
    rest: 'capturing',
    muscle: 'waiting',
    visual: 'processing',
    validation: 'processing',
    complete: 'success',
  };

  return states[step];
}

export function createInspectedCalibrationResult(
  step: CalibrationStep,
  state: CalibrationCaptureState,
): CalibrationResult {
  const result: CalibrationResult = { ...initialCalibrationResult };
  const stepIndex = calibrationSteps.indexOf(step);

  if (stepIndex > calibrationSteps.indexOf('rest')) result.rest = 'captured';
  if (stepIndex > calibrationSteps.indexOf('muscle')) {
    result.muscle = 'captured';
  }
  if (stepIndex > calibrationSteps.indexOf('visual')) {
    result.visual = 'adequate';
  }

  if (state === 'success') {
    if (step === 'rest') result.rest = 'captured';
    if (step === 'muscle') result.muscle = 'captured';
    if (step === 'visual') result.visual = 'adequate';
  }

  return result;
}

export function resolveCalibrationOrigin(
  value: string | string[] | undefined,
): CalibrationOrigin {
  return firstValue(value) === 'setup' ? 'setup' : 'hub';
}

export function resolveCalibrationInspection(
  stepValue: string | string[] | undefined,
  stateValue: string | string[] | undefined,
): CalibrationInspection | undefined {
  if (!__DEV__) return undefined;

  const requestedStep = firstValue(stepValue);
  const step = calibrationSteps.find(
    (candidate) => candidate === requestedStep,
  );
  if (!step) return undefined;

  const requestedState = firstValue(stateValue);
  const state = calibrationCaptureStates.find(
    (candidate) => candidate === requestedState,
  );

  return { step, state };
}

function firstValue(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}
