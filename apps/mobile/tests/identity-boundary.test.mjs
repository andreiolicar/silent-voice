import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createElement, useState } from 'react';
import { create, act } from 'react-test-renderer';
import { IdentityBoundary } from '../src/features/auth/IdentityBoundary.ts';
import { SessionCoordinator } from '../src/domain/auth/coordinator.ts';
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
test('A to B remounts private navigator and clears security secrets without intermediate logout', async () => {
  let seed = 'A secret';
  let mounts = 0;
  const snapshot = (id) => ({
    user: { id, name: id, email: `${id}@example.com`, emailVerified: true },
    expiresAt: '2030-01-01',
  });
  function SecurityScreen() {
    const [secret] = useState(() => {
      mounts++;
      return seed;
    });
    return createElement('security', { secret });
  }
  let renderer;
  let next = snapshot('A');
  const storage = {
    get: async () => null,
    set: async () => {},
    remove: async () => {},
  };
  let globalDevice = 'A connected';
  const engine = new SessionCoordinator({
    storage,
    persistentIdentity: false,
    connected: async () => true,
    readSession: async () => ({ kind: 'valid', snapshot: next }),
    cookie: async () => '',
    clearCredentials: async () => {},
    revoke: async () => true,
    resetUserState: () => {
      globalDevice = 'disconnected';
    },
    onChange: (state) => {
      if (renderer)
        renderer.update(
          createElement(
            IdentityBoundary,
            { identityKey: state.session?.user.id || 'guest' },
            createElement(SecurityScreen),
          ),
        );
    },
  });
  await engine.refresh();
  await act(async () => {
    renderer = create(
      createElement(
        IdentityBoundary,
        { identityKey: 'A' },
        createElement(SecurityScreen),
      ),
    );
  });
  assert.equal(renderer.root.findByType('security').props.secret, 'A secret');
  seed = 'B clean';
  next = snapshot('B');
  await act(async () => {
    await engine.refresh();
  });
  assert.equal(renderer.root.findByType('security').props.secret, 'B clean');
  assert.equal(mounts, 2);
  assert.equal(globalDevice, 'disconnected');
  await act(async () => renderer.unmount());
});
