/** Preparation only: no camera, detector, model, or biometric data is provided. */
export type CapturedFrame = {
  timestampNs: number;
  width: number;
  height: number;
  pixelFormat: string;
  orientation: string;
  mirrored: boolean;
};

export type VisualState =
  | { status: 'idle' | 'capturing' | 'processing' | 'cancelled' }
  | { status: 'recognized'; word: string }
  | {
      status:
        'rejected' | 'camera-error' | 'cadence-error' | 'model-unavailable';
    };

export type CaptureResult = {
  status: 'pass' | 'blocked';
  failures: string[];
  mapping: number[];
};

/** Subtract in native integer precision before passing relative nanoseconds as numbers. */
export function relativeCaptureTimestampNs(
  timestampNs: bigint,
  originNs: bigint,
): number {
  if (
    typeof timestampNs !== 'bigint' ||
    typeof originNs !== 'bigint' ||
    originNs < 0n
  ) {
    throw new TypeError('Expected nonnegative integer clock values.');
  }
  const relative = timestampNs - originNs;
  if (relative < 0n || relative > BigInt(Number.MAX_SAFE_INTEGER)) {
    throw new RangeError(
      'Relative timestamp is outside the exact integer range.',
    );
  }
  return Number(relative);
}

/** Timestamps are integer nanoseconds relative to the first captured frame. */
export function analyzeCapture(
  frames: CapturedFrame[],
  options: { readFailures?: number; interrupted?: boolean } = {},
): CaptureResult {
  const blocked = (reason: string): CaptureResult => ({
    status: 'blocked',
    failures: [reason],
    mapping: [],
  });
  if (
    frames.length < 2 ||
    frames[0].timestampNs !== 0 ||
    frames.some(
      (frame, index) =>
        !Number.isSafeInteger(frame.timestampNs) ||
        frame.timestampNs < 0 ||
        (index > 0 && frame.timestampNs <= frames[index - 1].timestampNs),
    )
  )
    return blocked('invalid-timestamps');
  if (
    frames.some(
      (frame) =>
        frame.width !== 640 ||
        frame.height !== 480 ||
        frame.pixelFormat !== 'BGR8' ||
        frame.orientation !== 'upright' ||
        frame.mirrored !== false,
    )
  )
    return blocked('invalid-frame');
  const readFailures = options.readFailures ?? 0;
  if (!Number.isSafeInteger(readFailures) || readFailures < 0) {
    return blocked('invalid-read-failures');
  }
  const relative = frames.map(
    (frame) => frame.timestampNs - frames[0].timestampNs,
  );
  const duration = relative[relative.length - 1] / 1e9;
  const fps = (relative.length - 1) / duration;
  const gaps = relative
    .slice(1)
    .map((value, index) => (value - relative[index]) / 1e9);
  const maxGap = Math.max(...gaps);
  const mapping: number[] = [];
  let source = 0;
  for (let index = 0; index < 121; index += 1) {
    const target = Math.round((index * 1e9) / 30);
    while (source + 1 < relative.length && relative[source + 1] <= target)
      source += 1;
    mapping.push(source);
  }
  const holds = mapping
    .slice(1)
    .filter((value, index) => value === mapping[index]).length;
  const perSecond = [0, 1, 2, 3].map(
    (second) =>
      relative.filter(
        (value) => second <= value / 1e9 && value / 1e9 < second + 1,
      ).length,
  );
  const failures: string[] = [];
  if (options.interrupted) failures.push('recording_interrupted');
  if (readFailures) failures.push('source_read_failure');
  if (duration < 4) failures.push('acquisition_too_short');
  if (duration > 4.15) failures.push('acquisition_too_long');
  if (fps < 27) failures.push('source_fps_below_minimum');
  if (maxGap > 0.15) failures.push('source_gap_above_maximum');
  if (holds > 24) {
    if (holds > 32) failures.push('hold_count_above_maximum');
    else {
      if (fps < 29) failures.push('conditional_source_fps_below_minimum');
      if (maxGap > 0.05) failures.push('conditional_source_gap_above_maximum');
      if (Math.min(...perSecond) < 27)
        failures.push('conditional_sustained_frame_loss');
    }
  }
  if (Math.abs(121 / 30 - duration) > 0.117)
    failures.push('acquisition_playback_mismatch');
  return { status: failures.length ? 'blocked' : 'pass', failures, mapping };
}

/** Explicitly unavailable until an approved native implementation exists. */
export async function startGlobalRecognition(_runtime: {
  available: boolean;
}): Promise<VisualState> {
  return { status: 'model-unavailable' };
}
