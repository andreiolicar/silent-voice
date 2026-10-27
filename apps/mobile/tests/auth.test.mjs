import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  resolveSession,
  validSnapshot,
  validateCredentials,
  flushRevocations,
} from '../src/domain/auth/policy.ts';
const cached = {
  user: {
    id: 'u1',
    name: 'Ana',
    email: 'ana@example.com',
    emailVerified: true,
  },
  expiresAt: '2030-01-01T00:00:00.000Z',
};
test('only previously verified nonexpired identity permits local offline access', () => {
  assert.equal(validSnapshot(cached, 0), true);
  assert.equal(
    validSnapshot(
      { ...cached, user: { ...cached.user, emailVerified: false } },
      0,
    ),
    false,
  );
  assert.equal(validSnapshot(cached, Date.parse('2031-01-01')), false);
  assert.equal(resolveSession(cached, { kind: 'transport' }, 0)?.user.id, 'u1');
  assert.equal(resolveSession(null, { kind: 'transport' }, 0), null);
});
test('explicit null, unauthorized and expiry cannot fall back to cache', () => {
  for (const result of [{ kind: 'invalid' }, { kind: 'valid', snapshot: null }])
    assert.equal(resolveSession(cached, result, 0), null);
  assert.equal(
    resolveSession(cached, { kind: 'transport' }, Date.parse('2031-01-01')),
    null,
  );
});
test('validation catches malformed identity, short passwords and mismatched confirmation', () => {
  assert.ok(validateCredentials('bad', 'short'));
  assert.ok(validateCredentials('a@b.com', 'long-password', 'different'));
  assert.equal(
    validateCredentials('a@b.com', 'long-password', 'long-password'),
    null,
  );
});
test('queued revocation uses captured credential and survives network errors', async () => {
  const calls = [];
  const pending = [{ cookie: 'old=session', expiresAt: cached.expiresAt }];
  assert.deepEqual(
    await flushRevocations(
      pending,
      async (cookie) => {
        calls.push(cookie);
        return false;
      },
      0,
    ),
    pending,
  );
  assert.deepEqual(
    await flushRevocations(
      pending,
      async (cookie) => {
        calls.push(cookie);
        return true;
      },
      0,
    ),
    [],
  );
  assert.deepEqual(calls, ['old=session', 'old=session']);
});
test('expired revocation credentials are discarded without transmission', async () => {
  let sent = false;
  assert.deepEqual(
    await flushRevocations(
      [{ cookie: 'expired', expiresAt: '2000-01-01' }],
      async () => {
        sent = true;
        return true;
      },
    ),
    [],
  );
  assert.equal(sent, false);
});
import { SessionCoordinator } from '../src/domain/auth/coordinator.ts';
function setup({
  snapshot = cached,
  connected = true,
  result = { kind: 'valid', snapshot: cached },
  read,
} = {}) {
  const events = [];
  const saved = new Map([
    ['sv.identity', JSON.stringify(snapshot)],
    ['sv.onboarding', '1'],
  ]);
  const engine = new SessionCoordinator({
    persistentIdentity: true,
    storage: {
      get: async (k) => saved.get(k) || null,
      set: async (k, v) => {
        saved.set(k, v);
      },
      remove: async (k) => {
        saved.delete(k);
      },
    },
    connected: async () => connected,
    readSession: read || (async () => result),
    cookie: async () => 'old=session',
    clearCredentials: async () => events.push('clear'),
    revoke: async (cookie) => {
      events.push(cookie);
      return true;
    },
    resetUserState: () => events.push('reset'),
    onChange: () => {},
    now: () => 0,
  });
  return { engine, events, saved };
}
test('boot offline reuses only valid confirmed snapshot', async () => {
  const { engine } = setup({ connected: false });
  await engine.boot();
  assert.equal(engine.state.session.user.id, 'u1');
  assert.equal(engine.state.offline, true);
  assert.equal(engine.state.onboarding, true);
});
test('SDK null response clears local identity and device state', async () => {
  const { engine, saved, events } = setup({
    result: { kind: 'valid', snapshot: null },
  });
  await engine.boot();
  assert.equal(engine.state.session, null);
  assert.equal(saved.has('sv.identity'), false);
  assert.ok(events.includes('reset'));
});
test('logout immediately clears UI while transport is still in flight, then clears cookies and queues exact old credential', async () => {
  let finish;
  const { engine, events, saved } = setup({
    read: () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  });
  const boot = engine.boot();
  while (!finish) await new Promise((resolve) => setTimeout(resolve, 0));
  const logout = engine.logout();
  assert.equal(engine.state.session, null);
  assert.ok(events.includes('reset'));
  finish({ kind: 'valid', snapshot: cached });
  await boot;
  await logout;
  assert.equal(engine.state.session, null);
  assert.equal(saved.get('sv.onboarding'), '1');
  assert.equal(saved.has('sv.identity'), false);
  assert.ok(events.includes('clear'));
  assert.equal(
    JSON.parse(saved.get('sv.revocations'))[0].cookie,
    'old=session',
  );
});
test('a later refresh drains queued old logout before reading a new session', async () => {
  const { engine, events, saved } = setup();
  await engine.boot();
  await engine.logout();
  assert.equal(engine.state.session, null);
  await engine.refresh();
  assert.ok(events.includes('old=session'));
  assert.deepEqual(JSON.parse(saved.get('sv.revocations')), []);
});
test('concurrent drains use a single captured credential request', async () => {
  const { engine, saved } = setup();
  await engine.boot();
  await engine.logout();
  const finishes = [];
  let calls = 0;
  engine.deps.revoke = async () => {
    calls++;
    return new Promise((resolve) => {
      finishes.push(resolve);
    });
  };
  const first = engine.drainQueue();
  const second = engine.drainQueue();
  await new Promise((resolve) => setTimeout(resolve, 0));
  for (const finish of finishes) finish(true);
  await Promise.all([first, second]);
  assert.equal(calls, 1);
  assert.deepEqual(JSON.parse(saved.get('sv.revocations')), []);
});
test('explicit invalidation clears credentials, identity and user state', async () => {
  const { engine, events, saved } = setup();
  await engine.boot();
  await engine.invalidate();
  assert.equal(engine.state.session, null);
  assert.equal(saved.has('sv.identity'), false);
  assert.ok(events.includes('clear'));
  assert.ok(events.includes('reset'));
});
function deferred() {
  let resolve;
  const promise = new Promise((done) => {
    resolve = done;
  });
  return { promise, resolve };
}
const tick = () => new Promise((resolve) => setTimeout(resolve, 0));
test('logout persists intent before held refresh; offline restart stays signed out and reconnect revokes A', async () => {
  const held = deferred();
  const { engine, saved } = setup({ read: () => held.promise });
  const original = engine.boot();
  await tick();
  const logout = engine.logout();
  await tick();
  const restarted = setup({ connected: false }).engine;
  restarted.deps.storage = engine.deps.storage;
  await restarted.boot();
  const offlineSession = restarted.state.session;
  const intent = saved.get('sv.logout');
  const revoked = [];
  restarted.deps.connected = async () => true;
  restarted.deps.revoke = async (cookie) => {
    revoked.push(cookie);
    return true;
  };
  await restarted.refresh();
  held.resolve({ kind: 'valid', snapshot: cached });
  await Promise.all([original, logout]);
  assert.equal(offlineSession, null);
  assert.ok(intent);
  assert.ok(revoked.includes('old=session'));
  assert.equal(restarted.state.session, null);
});
test('pending pre-login refresh cannot erase fresh login credentials and post-login reads again', async () => {
  const held = deferred();
  const { engine } = setup({ snapshot: null, read: () => held.promise });
  let cookie = '';
  engine.deps.cookie = async () => cookie;
  engine.deps.clearCredentials = async () => {
    cookie = '';
  };
  const original = engine.refresh();
  await tick();
  let entered = false;
  const action = engine.runAuthAction(
    async () => {
      entered = true;
      cookie = 'new-login-cookie';
      return { ok: true };
    },
    { sessionEffect: () => 'refresh' },
  );
  await tick();
  const enteredBeforeReadSettled = entered;
  engine.deps.readSession = async () => ({ kind: 'valid', snapshot: cached });
  held.resolve({ kind: 'valid', snapshot: null });
  await Promise.all([original, action]);
  assert.equal(enteredBeforeReadSettled, false);
  assert.equal(cookie, 'new-login-cookie');
  assert.equal(engine.state.session.user.id, 'u1');
});
for (const label of ['login', 'MFA completion'])
  test(`automatic refresh during ${label} waits for mutation and fresh session`, async () => {
    const { engine } = setup({
      snapshot: null,
      result: { kind: 'valid', snapshot: null },
    });
    await engine.boot();
    let cookie = '';
    let reads = 0;
    engine.deps.clearCredentials = async () => {
      cookie = '';
    };
    engine.deps.readSession = async () => {
      reads++;
      return { kind: 'valid', snapshot: cookie ? cached : null };
    };
    const held = deferred();
    let entered = false;
    const action = engine.runAuthAction(
      async () => {
        entered = true;
        await held.promise;
        cookie = 'new-cookie';
        return { ok: true };
      },
      { sessionEffect: () => 'refresh' },
    );
    while (!entered) await tick();
    const automatic = engine.refresh();
    await tick();
    const readsDuringMutation = reads;
    held.resolve();
    await Promise.all([action, automatic]);
    assert.equal(readsDuringMutation, 0);
    assert.equal(cookie, 'new-cookie');
    assert.equal(engine.state.session.user.id, 'u1');
    assert.equal(reads, 1);
  });
test('second-factor challenge survives foreground refresh until explicit completion', async () => {
  const { engine } = setup({
    snapshot: null,
    result: { kind: 'valid', snapshot: null },
  });
  await engine.boot();
  let cookie = '';
  let reads = 0;
  engine.deps.clearCredentials = async () => {
    cookie = '';
  };
  engine.deps.readSession = async () => {
    reads++;
    return { kind: 'valid', snapshot: cached };
  };
  await engine.runAuthAction(
    async () => {
      cookie = 'challenge-cookie';
      return { twoFactorRedirect: true };
    },
    { sessionEffect: () => 'challenge' },
  );
  await engine.refresh();
  assert.equal(reads, 0);
  assert.equal(cookie, 'challenge-cookie');
  assert.equal(engine.state.session, null);
  await engine.runAuthAction(
    async () => {
      cookie = 'authenticated-cookie';
      return { ok: true };
    },
    { sessionEffect: () => 'refresh' },
  );
  assert.equal(reads, 1);
  assert.equal(cookie, 'authenticated-cookie');
  assert.equal(engine.state.session.user.id, 'u1');
});
test(
  'logout cancels an auth action waiting on a held old read without deadlock',
  { timeout: 1000 },
  async () => {
    const held = deferred();
    const { engine, saved } = setup({ read: () => held.promise });
    const read = engine.boot();
    await tick();
    let mutated = false;
    const action = engine.runAuthAction(
      async () => {
        mutated = true;
        return {};
      },
      { sessionEffect: () => 'refresh' },
    );
    const rejected = assert.rejects(action, /interrompida/);
    await tick();
    const logout = engine.logout();
    await tick();
    assert.ok(saved.get('sv.logout'));
    held.resolve({ kind: 'valid', snapshot: null });
    await Promise.all([read, logout, rejected]);
    assert.equal(mutated, false);
    assert.equal(engine.state.session, null);
  },
);
test(
  'logout during SDK login clears and queues late newly issued credentials',
  { timeout: 1000 },
  async () => {
    const { engine, saved } = setup();
    await engine.boot();
    let cookie = 'old=session';
    engine.deps.cookie = async () => cookie;
    engine.deps.clearCredentials = async () => {
      cookie = '';
    };
    const held = deferred();
    let entered = false;
    const action = engine.runAuthAction(
      async () => {
        entered = true;
        await held.promise;
        cookie = 'rotated=session';
        return {};
      },
      { sessionEffect: () => 'refresh' },
    );
    const rejected = assert.rejects(action, /interrompida/);
    while (!entered) await tick();
    const logout = engine.logout();
    await tick();
    assert.ok(saved.get('sv.logout'));
    held.resolve();
    await Promise.all([logout, rejected]);
    assert.equal(engine.state.session, null);
    assert.equal(cookie, '');
    assert.deepEqual(
      JSON.parse(saved.get('sv.revocations')).map((item) => item.cookie),
      ['old=session', 'rotated=session'],
    );
  },
);
test('successful account replacement never falls back to A if B session confirmation loses transport', async () => {
  const { engine } = setup();
  await engine.boot();
  engine.deps.readSession = async () => ({ kind: 'transport' });
  await engine.runAuthAction(async () => ({ ok: true }), {
    sessionEffect: () => 'refresh',
    replaceIdentity: true,
  });
  assert.equal(engine.state.session, null);
  assert.equal(engine.state.offline, true);
});
test('A-owned account mutation queued behind login B never invokes its SDK callback', async () => {
  const { engine } = setup();
  await engine.boot();
  const held = deferred();
  let entered = false;
  let credentialOwner = 'u1';
  const invoked = [];
  engine.deps.readSession = async () => ({
    kind: 'valid',
    snapshot: { ...cached, user: { ...cached.user, id: credentialOwner } },
  });
  const login = engine.runAuthAction(
    async () => {
      entered = true;
      await held.promise;
      credentialOwner = 'B';
      return { ok: true };
    },
    { scope: 'public', replaceIdentity: true, sessionEffect: () => 'refresh' },
  );
  while (!entered) await tick();
  assert.equal(engine.state.session.user.id, 'u1');
  const account = engine.runAuthAction(
    async () => {
      invoked.push(credentialOwner);
      return {};
    },
    { scope: 'account', invalidateOnUnauthorized: true },
  );
  const outcome = account.then(
    () => null,
    (error) => error,
  );
  held.resolve();
  await login;
  const rejection = await outcome;
  assert.equal(engine.state.session.user.id, 'B');
  assert.deepEqual(invoked, []);
  assert.match(rejection?.message || '', /conta interrompida/);
});
test('public command queued under A remains public after explicit login B', async () => {
  const { engine } = setup();
  await engine.boot();
  const held = deferred();
  let entered = false;
  let owner = 'u1';
  const calls = [];
  engine.deps.readSession = async () => ({
    kind: 'valid',
    snapshot: { ...cached, user: { ...cached.user, id: owner } },
  });
  const login = engine.runAuthAction(
    async () => {
      entered = true;
      await held.promise;
      owner = 'B';
      return {};
    },
    { scope: 'public', replaceIdentity: true, sessionEffect: () => 'refresh' },
  );
  while (!entered) await tick();
  const publicAction = engine.runAuthAction(
    async () => {
      calls.push('fixed-email-recovery');
      return {};
    },
    { scope: 'public' },
  );
  held.resolve();
  await Promise.all([login, publicAction]);
  assert.deepEqual(calls, ['fixed-email-recovery']);
  assert.equal(engine.state.session.user.id, 'B');
});
test('anonymous account-scoped callback is rejected while anonymous public auth remains supported', async () => {
  const { engine } = setup({
    snapshot: null,
    result: { kind: 'valid', snapshot: null },
  });
  await engine.boot();
  const calls = [];
  const account = engine.runAuthAction(
    async () => {
      calls.push('account');
      return {};
    },
    { scope: 'account' },
  );
  const outcome = account.then(
    () => null,
    (error) => error,
  );
  await engine.runAuthAction(
    async () => {
      calls.push('public');
      return {};
    },
    { scope: 'public' },
  );
  assert.deepEqual(calls, ['public']);
  assert.match((await outcome)?.message || '', /conta interrompida/);
});
test('reauthentication to the same user cancels account closures from the older auth generation', async () => {
  const { engine } = setup();
  await engine.boot();
  const held = deferred();
  let entered = false;
  let invoked = false;
  const login = engine.runAuthAction(
    async () => {
      entered = true;
      await held.promise;
      return {};
    },
    { scope: 'public', replaceIdentity: true, sessionEffect: () => 'refresh' },
  );
  while (!entered) await tick();
  const old = engine.runAuthAction(
    async () => {
      invoked = true;
      return {};
    },
    { scope: 'account' },
  );
  const outcome = old.then(
    () => null,
    (error) => error,
  );
  held.resolve();
  await login;
  assert.equal(engine.state.session.user.id, 'u1');
  assert.match((await outcome)?.message || '', /conta interrompida/);
  assert.equal(invoked, false);
});
test('anonymous public recovery queued behind explicit login remains executable after authentication', async () => {
  const { engine } = setup({
    snapshot: null,
    result: { kind: 'valid', snapshot: null },
  });
  await engine.boot();
  const held = deferred();
  let entered = false;
  let called = false;
  engine.deps.readSession = async () => ({ kind: 'valid', snapshot: cached });
  const login = engine.runAuthAction(
    async () => {
      entered = true;
      await held.promise;
      return {};
    },
    { scope: 'public', replaceIdentity: true, sessionEffect: () => 'refresh' },
  );
  while (!entered) await tick();
  const recovery = engine.runAuthAction(
    async () => {
      called = true;
      return {};
    },
    { scope: 'public' },
  );
  held.resolve();
  await Promise.all([login, recovery]);
  assert.equal(called, true);
  assert.equal(engine.state.session.user.id, 'u1');
});
const SESSION_LIFETIME = 7 * 24 * 60 * 60 * 1000;
for (const rotated of [false, true])
  test(`pending ${rotated ? 'rotated' : 'same-cookie renewed'} session keeps revocation past cached expiry and offline restart`, async () => {
    let now = 0;
    const initial = { ...cached, expiresAt: new Date(1000).toISOString() };
    const { engine, saved } = setup({
      snapshot: initial,
      result: { kind: 'valid', snapshot: initial },
    });
    engine.deps.now = () => now;
    let cookie = 'captured=old';
    engine.deps.cookie = async () => cookie;
    engine.deps.clearCredentials = async () => {
      cookie = '';
    };
    await engine.boot();
    const held = deferred();
    engine.deps.readSession = () => held.promise;
    const read = engine.refresh();
    await tick();
    const logout = engine.logout();
    await tick();
    now = 500;
    if (rotated) cookie = 'captured=rotated';
    held.resolve({
      kind: 'valid',
      snapshot: {
        ...initial,
        expiresAt: new Date(now + SESSION_LIFETIME).toISOString(),
      },
    });
    await Promise.all([read, logout]);
    const pending = JSON.parse(saved.get('sv.revocations'));
    const target = rotated ? 'captured=rotated' : 'captured=old';
    const queued = pending.find((item) => item.cookie === target);
    const durable = JSON.parse(saved.get('sv.logout'));
    now = 2000;
    const restarted = setup({ connected: false }).engine;
    restarted.deps.storage = engine.deps.storage;
    restarted.deps.now = () => now;
    restarted.deps.cookie = async () => cookie;
    restarted.deps.clearCredentials = engine.deps.clearCredentials;
    await restarted.boot();
    const revoked = [];
    restarted.deps.connected = async () => true;
    restarted.deps.revoke = async (exact) => {
      revoked.push(exact);
      return true;
    };
    await restarted.refresh();
    assert.equal(restarted.state.session, null);
    assert.ok(revoked.includes(target));
    assert.ok(Date.parse(queued.expiresAt) >= 500 + SESSION_LIFETIME);
    assert.ok(Date.parse(durable.expiresAt) >= Date.parse(queued.expiresAt));
    if (!rotated) assert.equal(pending.length, 1);
  });
test('logout entries beyond conservative seven-day capture bound are discarded without sending credentials', async () => {
  let now = 0;
  const initial = { ...cached, expiresAt: new Date(1000).toISOString() };
  const { engine, saved } = setup({
    snapshot: initial,
    result: { kind: 'valid', snapshot: initial },
  });
  engine.deps.now = () => now;
  await engine.boot();
  await engine.logout();
  now = SESSION_LIFETIME + 1;
  let called = false;
  engine.deps.revoke = async () => {
    called = true;
    return true;
  };
  await engine.drainQueue();
  assert.equal(called, false);
  assert.deepEqual(JSON.parse(saved.get('sv.revocations')), []);
});
test('pending revocation drain preserves a same-cookie deadline extended by logout capture', async () => {
  const initial = { ...cached, expiresAt: new Date(1000).toISOString() };
  const { engine, saved } = setup({
    snapshot: initial,
    result: { kind: 'valid', snapshot: initial },
  });
  await engine.boot();
  saved.set(
    'sv.revocations',
    JSON.stringify([
      {
        cookie: 'old=session',
        userId: 'u1',
        expiresAt: new Date(1000).toISOString(),
      },
    ]),
  );
  const held = deferred();
  engine.deps.revoke = () => held.promise;
  const draining = engine.drainQueue();
  await tick();
  await engine.logout();
  held.resolve(false);
  await draining;
  const pending = JSON.parse(saved.get('sv.revocations'));
  assert.equal(pending.length, 1);
  assert.ok(Date.parse(pending[0].expiresAt) >= SESSION_LIFETIME);
  assert.ok(
    Date.parse(JSON.parse(saved.get('sv.logout')).expiresAt) >=
      Date.parse(pending[0].expiresAt),
  );
});
