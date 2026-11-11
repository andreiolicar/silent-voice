import { analyzeCapture, type CapturedFrame } from './contract.ts';
import bgr8Reference from './data/bgr8-reference.json' with { type: 'json' };

export type SyntheticNormalizationReport = {
  width: number;
  height: number;
  pixelFormat: string;
  byteCount: number;
  sha256: string;
  samples: { offset: number; value: number }[];
};

export function verifySyntheticNormalization(
  report: SyntheticNormalizationReport,
) {
  return (
    report.width === bgr8Reference.width &&
    report.height === bgr8Reference.height &&
    report.pixelFormat === bgr8Reference.pixelFormat &&
    report.byteCount === bgr8Reference.byteCount &&
    report.sha256 === bgr8Reference.sha256 &&
    report.samples.length === bgr8Reference.samples.length &&
    report.samples.every(
      (sample, index) =>
        sample.offset === bgr8Reference.samples[index].offset &&
        sample.value === bgr8Reference.samples[index].value,
    )
  );
}

export type CameraPermission =
  'undetermined' | 'granted' | 'denied' | 'restricted';
export type NativeCaptureReport = {
  status: 'complete' | 'cancelled' | 'camera-error';
  frames: CapturedFrame[];
  readFailures: number;
  error?: string;
  source?: Omit<CapturedFrame, 'timestampNs'> & {
    byteCount?: number;
    bytesPerRow?: number;
  };
  normalization?: {
    status: 'complete' | 'blocked';
    frameCount: number;
    byteCountPerFrame: number;
  };
};

export function isIosLabEnabled(platform: string, flag: string | undefined) {
  return platform === 'ios' && flag === '1';
}

export function verifySyntheticCapture(frames: CapturedFrame[]) {
  const contract = analyzeCapture(frames);
  const timestampsMatch =
    frames.length === 121 &&
    frames.every(
      (frame, index) => frame.timestampNs === Math.round((index * 1e9) / 30),
    );
  const mappingMatches =
    contract.mapping.length === 121 &&
    contract.mapping.every((source, index) => source === index);
  return {
    passed: timestampsMatch && mappingMatches && contract.status === 'pass',
    timestampsMatch,
    mappingMatches,
    contract,
  };
}

export function summarizeCapture(report: NativeCaptureReport) {
  const { frames } = report;
  const validClock =
    frames.length >= 2 &&
    frames[0].timestampNs === 0 &&
    frames.every(
      (frame, index) =>
        Number.isSafeInteger(frame.timestampNs) &&
        frame.timestampNs >= 0 &&
        (index === 0 || frame.timestampNs > frames[index - 1].timestampNs),
    );
  const durationSeconds = validClock
    ? frames[frames.length - 1].timestampNs / 1e9
    : null;
  const first = frames[0];
  const normalizationValid =
    !report.normalization ||
    (report.normalization.status === 'complete' &&
      report.normalization.frameCount === frames.length &&
      report.normalization.byteCountPerFrame === 921600);
  return {
    status: report.status,
    error: report.error,
    frameCount: frames.length,
    durationSeconds,
    fps: durationSeconds ? (frames.length - 1) / durationSeconds : null,
    readFailures: report.readFailures,
    pixelFormat: first?.pixelFormat ?? 'unknown',
    dimensions: first ? `${first.width} × ${first.height}` : 'unknown',
    orientation: first?.orientation ?? 'unknown',
    mirrored: first?.mirrored ?? null,
    sourcePixelFormat:
      report.source?.pixelFormat ?? first?.pixelFormat ?? 'unknown',
    sourceByteCount: report.source?.byteCount ?? null,
    sourceBytesPerRow: report.source?.bytesPerRow ?? null,
    sourceDimensions: report.source
      ? `${report.source.width} × ${report.source.height}`
      : first
        ? `${first.width} × ${first.height}`
        : 'unknown',
    normalizationStatus: report.normalization?.status ?? 'unavailable',
    byteCountPerFrame: report.normalization?.byteCountPerFrame ?? null,
    contract: analyzeCapture(frames, {
      readFailures: report.readFailures,
      interrupted: report.status !== 'complete' || !normalizationValid,
    }),
  };
}
