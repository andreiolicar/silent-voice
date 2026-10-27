import { useCallback, useEffect, useMemo, useState } from 'react';

import type {
  CalibrationCaptureState,
  CalibrationResult,
  CalibrationStep,
} from '@/domain/calibration';

import {
  createInspectedCalibrationResult,
  getInitialCalibrationState,
  initialCalibrationResult,
  mockCalibrationSequences,
} from '../data/calibration.mock';

type UseMockCalibrationFlowOptions = {
  inspectedState?: CalibrationCaptureState;
  inspectedStep?: CalibrationStep;
};

export type MockCalibrationFlow = {
  advance: () => void;
  captureState: CalibrationCaptureState;
  result: CalibrationResult;
  retryCurrentStep: () => void;
  step: CalibrationStep;
};

const VALIDATION_COMPLETE_DELAY = 1900;

export function useMockCalibrationFlow({
  inspectedState,
  inspectedStep,
}: UseMockCalibrationFlowOptions = {}): MockCalibrationFlow {
  const initialStep = inspectedStep ?? 'preparation';
  const initialState =
    inspectedState ?? getInitialCalibrationState(initialStep);
  const [step, setStep] = useState<CalibrationStep>(initialStep);
  const [captureState, setCaptureState] =
    useState<CalibrationCaptureState>(initialState);
  const [result, setResult] = useState<CalibrationResult>(() =>
    inspectedStep
      ? createInspectedCalibrationResult(inspectedStep, initialState)
      : initialCalibrationResult,
  );
  const [restartVersion, setRestartVersion] = useState(0);

  useEffect(() => {
    if (inspectedStep) return;

    const sequence = mockCalibrationSequences[step] ?? [];
    const timers = sequence.map((transition) =>
      setTimeout(() => {
        setCaptureState(transition.state);
        if (transition.state === 'success') {
          setResult((current) => resultAfterSuccess(current, step));
        }
      }, transition.afterMs),
    );

    if (step === 'validation') {
      timers.push(
        setTimeout(() => {
          setStep('complete');
          setCaptureState('success');
        }, VALIDATION_COMPLETE_DELAY),
      );
    }

    return () => timers.forEach(clearTimeout);
  }, [inspectedStep, restartVersion, step]);

  const displayedStep = inspectedStep ?? step;
  const displayedState = inspectedStep
    ? (inspectedState ?? getInitialCalibrationState(inspectedStep))
    : captureState;
  const displayedResult = useMemo(
    () =>
      inspectedStep
        ? createInspectedCalibrationResult(inspectedStep, displayedState)
        : result,
    [displayedState, inspectedStep, result],
  );

  const moveTo = useCallback((nextStep: CalibrationStep) => {
    setStep(nextStep);
    setCaptureState(getInitialCalibrationState(nextStep));
  }, []);

  const advance = useCallback(() => {
    if (displayedStep === 'preparation') moveTo('rest');
    if (displayedStep === 'rest' && displayedState === 'success') {
      moveTo('muscle');
    }
    if (displayedStep === 'muscle' && displayedState === 'success') {
      moveTo('visual');
    }
    if (displayedStep === 'visual' && displayedState === 'success') {
      moveTo('validation');
    }
  }, [displayedState, displayedStep, moveTo]);

  const retryCurrentStep = useCallback(() => {
    setStep(displayedStep);
    setCaptureState(getInitialCalibrationState(displayedStep));
    setRestartVersion((current) => current + 1);
  }, [displayedStep]);

  return {
    advance,
    captureState: displayedState,
    result: displayedResult,
    retryCurrentStep,
    step: displayedStep,
  };
}

function resultAfterSuccess(
  current: CalibrationResult,
  step: CalibrationStep,
): CalibrationResult {
  if (step === 'rest') return { ...current, rest: 'captured' };
  if (step === 'muscle') return { ...current, muscle: 'captured' };
  if (step === 'visual') return { ...current, visual: 'adequate' };
  return current;
}
