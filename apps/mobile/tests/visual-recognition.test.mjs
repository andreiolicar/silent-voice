import assert from 'node:assert/strict';
import test from 'node:test';

import * as contract from '../src/features/visual-recognition/contract.ts';
const { analyzeCapture, relativeCaptureTimestampNs, startGlobalRecognition } =
  contract;

const frames = (fps, durationSeconds = 4) =>
  Array.from({ length: fps * durationSeconds + 1 }, (_, index) => ({
    timestampNs: Math.round((index * 1e9) / fps),
    width: 640,
    height: 480,
    pixelFormat: 'BGR8',
    orientation: 'upright',
    mirrored: false,
  }));

test('maps 121 positions to acquired frames, preserving indices', () => {
  const result = analyzeCapture(frames(30));
  assert.equal(result.status, 'pass');
  assert.equal(result.mapping.length, 121);
  assert.equal(result.mapping[0], 0);
  assert.equal(result.mapping[120], 120);
  assert.deepEqual(
    result.mapping,
    Array.from({ length: 121 }, (_, i) => i),
  );
});

test('blocks invalid dimensions, format, orientation and mirror', () => {
  for (const change of [
    { width: 480 },
    { pixelFormat: 'RGB8' },
    { orientation: 'rotated' },
    { mirrored: true },
  ]) {
    const input = frames(30);
    input[0] = { ...input[0], ...change };
    assert.equal(analyzeCapture(input).status, 'blocked');
  }
});

test('blocks invalid timestamps, low cadence, gaps and capture errors', () => {
  const repeated = frames(30);
  repeated[2].timestampNs = repeated[1].timestampNs;
  assert.equal(analyzeCapture(repeated).status, 'blocked');
  assert.equal(analyzeCapture(frames(26)).status, 'blocked');
  const gap = frames(30).filter((_, i) => i < 40 || i > 45);
  assert.equal(analyzeCapture(gap).status, 'blocked');
  assert.equal(
    analyzeCapture(frames(30), { readFailures: 1 }).status,
    'blocked',
  );
  assert.equal(
    analyzeCapture(frames(30), { interrupted: true }).status,
    'blocked',
  );
});

test('does not invent a recognized word if private runtime is unavailable', async () => {
  const result = await startGlobalRecognition({ available: false });
  assert.deepEqual(result, { status: 'model-unavailable' });
  assert.equal('word' in result, false);
});

test('does not enable recognition from an availability flag alone', async () => {
  assert.deepEqual(await startGlobalRecognition({ available: true }), {
    status: 'model-unavailable',
  });
});

test('blocks empty and single-frame captures without throwing', () => {
  for (const input of [[], frames(30).slice(0, 1)]) {
    assert.deepEqual(analyzeCapture(input), {
      status: 'blocked',
      failures: ['invalid-timestamps'],
      mapping: [],
    });
  }
});

test('requires the mirror flag to be exactly false', () => {
  for (const value of [undefined, null, 0, '', 'false', true]) {
    const input = frames(30);
    input[0].mirrored = value;
    assert.equal(analyzeCapture(input).status, 'blocked', String(value));
  }
  const input = frames(30);
  delete input[0].mirrored;
  assert.equal(analyzeCapture(input).status, 'blocked');
});

test('subtracts high-precision absolute timestamps before conversion', () => {
  const origin = 9_000_000_000_000_000_000n;
  assert.equal(
    relativeCaptureTimestampNs(origin + 123_456_789n, origin),
    123_456_789,
  );
  assert.throws(() => relativeCaptureTimestampNs(origin - 1n, origin));
  assert.throws(() =>
    relativeCaptureTimestampNs(origin + 9_007_199_254_740_992n, origin),
  );
  assert.throws(() => relativeCaptureTimestampNs(Number(origin), 0n));
  assert.throws(() => relativeCaptureTimestampNs(0n, -1n));
  const input = frames(30);
  input[0].timestampNs = 1;
  assert.equal(analyzeCapture(input).status, 'blocked');
  const translated = frames(30).map((frame) => ({
    ...frame,
    timestampNs: relativeCaptureTimestampNs(
      origin + BigInt(frame.timestampNs),
      origin,
    ),
  }));
  assert.deepEqual(analyzeCapture(translated), analyzeCapture(frames(30)));
});

test('rejects invalid timestamps and read-failure counts', () => {
  for (const value of [-1, NaN, Infinity, 1.5, Number.MAX_SAFE_INTEGER + 1]) {
    const input = frames(30);
    input[1].timestampNs = value;
    assert.equal(analyzeCapture(input).status, 'blocked');
  }
  for (const readFailures of [-1, 1.5, NaN]) {
    assert.equal(
      analyzeCapture(frames(30), { readFailures }).status,
      'blocked',
    );
  }
});

test('applies duration boundaries at nanosecond resolution', () => {
  for (const [duration, accepted] of [
    [3_999_999_999, false],
    [4_000_000_000, true],
    [4_150_000_000, true],
    [4_150_000_001, false],
  ]) {
    const input = frames(30).map((frame, i) => ({
      ...frame,
      timestampNs: Math.round((i * duration) / 120),
    }));
    assert.equal(
      analyzeCapture(input).status === 'pass',
      accepted,
      String(duration),
    );
  }
});

test('applies the 27 fps and 150 ms gap thresholds', () => {
  const atFps = frames(27);
  assert.ok(
    !analyzeCapture(atFps).failures.includes('source_fps_below_minimum'),
  );
  const belowFps = frames(27);
  belowFps.splice(1, 1);
  assert.ok(
    analyzeCapture(belowFps).failures.includes('source_fps_below_minimum'),
  );
  const atGap = frames(30).filter(
    (_, i) => i !== 31 && i !== 32 && i !== 33 && i !== 34,
  );
  atGap.find((f) => f.timestampNs > 1_000_000_000).timestampNs = 1_150_000_000;
  assert.ok(
    !analyzeCapture(atGap).failures.includes('source_gap_above_maximum'),
  );
  atGap.find((f) => f.timestampNs === 1_150_000_000).timestampNs += 1;
  assert.ok(
    analyzeCapture(atGap).failures.includes('source_gap_above_maximum'),
  );
});

test('applies conditional hold limits of 24, 25, 32 and 33', () => {
  for (const count of [24, 25, 32, 33]) {
    const input = frames(30);
    for (let i = 0; i < count; i++) input[2 + i * 3].timestampNs += 1;
    const result = analyzeCapture(input);
    const holds = result.mapping
      .slice(1)
      .filter((value, i) => value === result.mapping[i]).length;
    assert.equal(holds, count);
    assert.equal(result.status, count === 33 ? 'blocked' : 'pass');
    assert.equal(
      result.failures.includes('hold_count_above_maximum'),
      count === 33,
    );
  }
});
