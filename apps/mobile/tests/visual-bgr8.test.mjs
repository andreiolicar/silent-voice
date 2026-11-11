import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import {
  summarizeCapture,
  verifySyntheticNormalization,
} from '../src/features/visual-recognition/capture-diagnostics.ts';

const reference = JSON.parse(
  await readFile(
    new URL(
      '../src/features/visual-recognition/data/bgr8-reference.json',
      import.meta.url,
    ),
    'utf8',
  ),
);
const temporal = JSON.parse(
  await readFile(
    new URL('./fixtures/visual-recognition.json', import.meta.url),
    'utf8',
  ),
);

test('checks the exact independent synthetic BGR reference and detects corruption', () => {
  assert.equal(verifySyntheticNormalization(reference), true);
  for (const change of [
    { sha256: '0'.repeat(64) },
    { byteCount: 1228800 },
    { pixelFormat: 'RGB8' },
    { width: 480 },
    { height: 640 },
    { samples: [] },
  ]) {
    assert.equal(
      verifySyntheticNormalization({ ...reference, ...change }),
      false,
    );
  }
  const changed = structuredClone(reference);
  changed.samples[0].value++;
  assert.equal(verifySyntheticNormalization(changed), false);
});

function normalizedReport() {
  return {
    status: 'complete',
    readFailures: 0,
    source: {
      width: 640,
      height: 480,
      pixelFormat: 'BGRA32',
      orientation: 'landscapeRight',
      mirrored: false,
      byteCount: 1228800,
      bytesPerRow: 2560,
    },
    frames: temporal.temporal.timestamps_ns.map((timestampNs) => ({
      timestampNs,
      width: 640,
      height: 480,
      pixelFormat: 'BGR8',
      orientation: 'upright',
      mirrored: false,
    })),
    normalization: {
      status: 'complete',
      frameCount: 121,
      byteCountPerFrame: 921600,
    },
  };
}

test('separates camera origin from a converted BGR buffer when applying the gate', () => {
  const result = summarizeCapture(normalizedReport());
  assert.equal(result.sourcePixelFormat, 'BGRA32');
  assert.equal(result.sourceDimensions, '640 × 480');
  assert.equal(result.sourceByteCount, 1228800);
  assert.equal(result.sourceBytesPerRow, 2560);
  assert.equal(result.pixelFormat, 'BGR8');
  assert.equal(result.normalizationStatus, 'complete');
  assert.equal(result.byteCountPerFrame, 921600);
  assert.equal(result.contract.status, 'pass');
});

test('failed or inconsistent normalization never passes even with valid-looking metadata', () => {
  for (const normalization of [
    { status: 'blocked', frameCount: 121, byteCountPerFrame: 921600 },
    { status: 'complete', frameCount: 120, byteCountPerFrame: 921600 },
    { status: 'complete', frameCount: 121, byteCountPerFrame: 1228800 },
  ]) {
    assert.equal(
      summarizeCapture({ ...normalizedReport(), normalization }).contract
        .status,
      'blocked',
    );
  }
  assert.equal(
    summarizeCapture({ ...normalizedReport(), status: 'camera-error' }).contract
      .status,
    'blocked',
  );
});
