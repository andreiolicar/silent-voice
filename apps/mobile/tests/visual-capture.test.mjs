import assert from 'node:assert/strict';
import test from 'node:test';
import { readFile } from 'node:fs/promises';
import { labReturnDestination } from '../src/features/visual-recognition/lab-navigation.ts';
import {
  isIosLabEnabled,
  summarizeCapture,
  verifySyntheticCapture,
} from '../src/features/visual-recognition/capture-diagnostics.ts';

const fixture = JSON.parse(
  await readFile(
    new URL('./fixtures/visual-recognition.json', import.meta.url),
    'utf8',
  ),
);
const frames = () =>
  fixture.temporal.timestamps_ns.map((timestampNs) => ({
    timestampNs,
    width: 640,
    height: 480,
    pixelFormat: 'BGR8',
    orientation: 'upright',
    mirrored: false,
  }));

test('leaving the lab preserves the authenticated and onboarding destinations', () => {
  assert.equal(labReturnDestination(true, true), '/(main)/home');
  assert.equal(labReturnDestination(true, false), '/(main)/home');
  assert.equal(labReturnDestination(false, true), '/auth/login');
  assert.equal(labReturnDestination(false, false), '/onboarding');
});

test('lab is enabled only for the explicit iOS build flag', () => {
  assert.equal(isIosLabEnabled('ios', '1'), true);
  for (const [platform, flag] of [
    ['ios', undefined],
    ['ios', 'true'],
    ['android', '1'],
    ['web', '1'],
  ]) {
    assert.equal(isIosLabEnabled(platform, flag), false);
  }
});

test('synthetic verification accepts the Python temporal reference and detects altered clocks', () => {
  assert.equal(verifySyntheticCapture(frames()).passed, true);
  const changed = frames();
  changed[1].timestampNs++;
  assert.equal(verifySyntheticCapture(changed).passed, false);
  assert.equal(verifySyntheticCapture(frames().slice(0, 120)).passed, false);
  const mirrored = frames();
  mirrored[0].mirrored = true;
  assert.equal(verifySyntheticCapture(mirrored).passed, false);
});

test('camera metadata reports source format and remains blocked before normalization', () => {
  const source = frames().map((frame) => ({
    ...frame,
    width: 480,
    height: 640,
    pixelFormat: 'BGRA32',
    orientation: 'portrait',
  }));
  const actual = summarizeCapture({
    status: 'complete',
    frames: source,
    readFailures: 2,
  });
  assert.equal(actual.frameCount, 121);
  assert.equal(actual.durationSeconds, 4);
  assert.equal(actual.fps, 30);
  assert.equal(actual.pixelFormat, 'BGRA32');
  assert.equal(actual.dimensions, '480 × 640');
  assert.equal(actual.readFailures, 2);
  assert.equal(actual.contract.status, 'blocked');
  assert.ok(actual.contract.failures.includes('invalid-frame'));
});

test('cancelled capture and invalid timestamps never produce a valid acquisition', () => {
  const cancelled = summarizeCapture({
    status: 'cancelled',
    frames: frames(),
    readFailures: 0,
  });
  assert.equal(cancelled.status, 'cancelled');
  assert.equal(cancelled.contract.status, 'blocked');
  const invalid = frames();
  invalid[1].timestampNs = 0;
  const result = summarizeCapture({
    status: 'camera-error',
    error: 'invalid-timestamps',
    frames: invalid,
    readFailures: 0,
  });
  assert.equal(result.fps, null);
  assert.equal(result.contract.status, 'blocked');
  assert.equal(result.error, 'invalid-timestamps');
  assert.equal(
    summarizeCapture({ status: 'camera-error', frames: [], readFailures: 0 })
      .fps,
    null,
  );
});
