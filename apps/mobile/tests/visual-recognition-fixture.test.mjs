import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

import { analyzeCapture } from '../src/features/visual-recognition/contract.ts';

test('synthetic Python and TypeScript agree on the temporal fixture', async () => {
  const fixture = JSON.parse(
    await readFile(
      new URL('./fixtures/visual-recognition.json', import.meta.url),
      'utf8',
    ),
  );
  const frames = fixture.temporal.timestamps_ns.map((timestampNs) => ({
    timestampNs,
    width: 640,
    height: 480,
    pixelFormat: 'BGR8',
    orientation: 'upright',
    mirrored: false,
  }));
  const actual = analyzeCapture(frames);
  assert.equal(actual.status, 'pass');
  assert.equal(fixture.temporal.decision, 'PASS');
  assert.deepEqual(actual.mapping, fixture.temporal.mapping);
  assert.equal(
    actual.mapping.slice(1).filter((v, i) => v === actual.mapping[i]).length,
    fixture.temporal.holds,
  );
});
