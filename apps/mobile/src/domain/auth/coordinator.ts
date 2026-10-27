import {
  flushRevocations,
  resolveSession,
  validSnapshot,
  type PendingRevocation,
  type SessionResult,
  type SessionSnapshot,
} from './policy.ts';
export type AuthState = {
  ready: boolean;
  onboarding: boolean;
  session: SessionSnapshot | null;
  offline: boolean;
};
type Storage = {
  get(key: string): Promise<string | null>;
  set(key: string, value: string): Promise<void>;
  remove(key: string): Promise<void>;
};
type Dependencies = {
  persistentIdentity: boolean;
  storage: Storage;
  connected(): Promise<boolean>;
  readSession(): Promise<SessionResult>;
  cookie(): Promise<string>;
  clearCredentials(): Promise<void>;
  revoke(cookie: string, userId?: string): Promise<boolean>;
  resetUserState(): void;
  onChange(state: AuthState): void;
  now?(): number;
};
export type AuthActionOptions<T> = {
  scope?: 'account' | 'public';
  sessionEffect?: (result: T) => 'refresh' | 'challenge' | 'none';
  invalidateOnUnauthorized?: boolean;
  replaceIdentity?: boolean;
};
type LogoutIntent = { userId?: string; expiresAt: string };
// Backend contract: a newly issued or renewed session lives at most seven days.
const SERVER_SESSION_LIFETIME_MS = 7 * 24 * 60 * 60 * 1000;
const CACHE = 'sv.identity',
  INTRO = 'sv.onboarding',
  QUEUE = 'sv.revocations',
  LOGOUT = 'sv.logout';
/** All native dependencies and SDK calls are injected; safe in plain Node. */
export class SessionCoordinator {
  state: AuthState = {
    ready: false,
    onboarding: false,
    session: null,
    offline: false,
  };
  private epoch = 0;
  private identityGeneration = 0;
  private logoutGeneration = 0;
  private inFlight: Promise<void> | null = null;
  private queueWrites: Promise<void> = Promise.resolve();
  private draining: Promise<boolean> | null = null;
  private signingOut: Promise<void> | null = null;
  private actionTail: Promise<void> = Promise.resolve();
  private actionPending = 0;
  private loggedOut = false;
  private challengePending = false;
  private deps: Dependencies;
  constructor(deps: Dependencies) {
    this.deps = deps;
  }
  private now() {
    return this.deps.now?.() ?? Date.now();
  }
  private update(patch: Partial<AuthState>) {
    if (
      'session' in patch &&
      this.state.session?.user.id !== patch.session?.user.id
    )
      this.identityGeneration++;
    this.state = { ...this.state, ...patch };
    this.deps.onChange(this.state);
  }
  private async apply(session: SessionSnapshot | null) {
    const previous = this.state.session;
    if (!session || (previous && previous.user.id !== session.user.id))
      this.deps.resetUserState();
    this.update({ session });
    if (session && this.deps.persistentIdentity)
      await this.deps.storage.set(CACHE, JSON.stringify(session));
    else await this.deps.storage.remove(CACHE);
  }
  private async pendingRevocations(): Promise<PendingRevocation[]> {
    try {
      const value = JSON.parse((await this.deps.storage.get(QUEUE)) || '[]');
      return Array.isArray(value)
        ? value.filter(
            (x) =>
              x &&
              typeof x.cookie === 'string' &&
              Number.isFinite(Date.parse(x.expiresAt)),
          )
        : [];
    } catch {
      return [];
    }
  }
  private updatePending(
    change: (current: PendingRevocation[]) => PendingRevocation[],
  ): Promise<void> {
    const write = this.queueWrites.then(async () => {
      const current = await this.pendingRevocations();
      await this.deps.storage.set(QUEUE, JSON.stringify(change(current)));
    });
    this.queueWrites = write.catch(() => {});
    return write;
  }
  private async captureRevocation(intent: LogoutIntent) {
    const cookie = await this.deps.cookie();
    if (!cookie && this.deps.persistentIdentity) return;
    // The ignored SDK response can renew the same token or rotate it. Bound its
    // validity from this capture, including the final capture after SDK work.
    intent.expiresAt = new Date(
      Math.max(
        Date.parse(intent.expiresAt) || 0,
        this.now() + SERVER_SESSION_LIFETIME_MS,
      ),
    ).toISOString();
    await this.deps.storage.set(LOGOUT, JSON.stringify(intent));
    await this.updatePending((current) => {
      const existing = current.find(
        (x) => x.cookie === cookie && x.userId === intent.userId,
      );
      if (!existing) return [...current, { ...intent, cookie }];
      intent.expiresAt = new Date(
        Math.max(Date.parse(existing.expiresAt), Date.parse(intent.expiresAt)),
      ).toISOString();
      return current.map((x) =>
        x === existing ? { ...x, expiresAt: intent.expiresAt } : x,
      );
    });
    // Keep recovery's durable deadline at least as late as the deduplicated queue.
    await this.deps.storage.set(LOGOUT, JSON.stringify(intent));
  }
  private async recoverLogout(intent: LogoutIntent) {
    this.loggedOut = true;
    await this.captureRevocation(intent);
    await this.deps.storage.remove(CACHE);
    await this.deps.clearCredentials();
  }
  async boot() {
    try {
      this.update({ onboarding: (await this.deps.storage.get(INTRO)) === '1' });
      const intent = await this.deps.storage.get(LOGOUT);
      if (intent) {
        let value: LogoutIntent;
        try {
          value = JSON.parse(intent);
        } catch {
          value = {
            expiresAt: new Date(
              this.now() + SERVER_SESSION_LIFETIME_MS,
            ).toISOString(),
          };
        }
        await this.recoverLogout(value);
      } else {
        const raw = this.deps.persistentIdentity
          ? await this.deps.storage.get(CACHE)
          : null;
        let cached: unknown = null;
        try {
          cached = raw ? JSON.parse(raw) : null;
        } catch {}
        if (validSnapshot(cached, this.now())) this.update({ session: cached });
      }
      await this.refresh();
    } finally {
      this.update({ ready: true });
    }
  }
  async finishOnboarding() {
    await this.deps.storage.set(INTRO, '1');
    this.update({ onboarding: true });
  }
  drainQueue(): Promise<boolean> {
    if (this.draining) return this.draining;
    this.draining = this.performDrainQueue().finally(() => {
      this.draining = null;
    });
    return this.draining;
  }
  private async performDrainQueue() {
    const pending = await this.pendingRevocations();
    const remaining = await flushRevocations(
      pending,
      this.deps.revoke,
      this.now(),
    );
    // Logout can append its intent while this network call is pending.
    let added: PendingRevocation[] = [];
    await this.updatePending((current) => {
      added = current.filter(
        (x) =>
          !pending.some(
            (original) =>
              original.cookie === x.cookie &&
              original.userId === x.userId &&
              Date.parse(original.expiresAt) >= Date.parse(x.expiresAt),
          ),
      );
      return [
        ...remaining.filter(
          (x) =>
            !added.some(
              (newer) => newer.cookie === x.cookie && newer.userId === x.userId,
            ),
        ),
        ...added,
      ];
    });
    return remaining.length === 0 && added.length === 0;
  }
  async prepareOnlineAction() {
    if (this.signingOut) await this.signingOut;
    if (!(await this.deps.connected()) || !(await this.drainQueue()))
      throw new Error('Conecte-se para concluir a saída anterior e continuar.');
  }
  /** Own the mutation AND its fresh session read. Listeners cannot read old cookies inside this boundary. */
  runAuthAction<T>(
    action: () => Promise<T>,
    options: AuthActionOptions<T> = {},
  ): Promise<T> {
    const submittedLogout = this.logoutGeneration;
    const submittedOwner = this.state.session?.user.id;
    const submittedIdentityGeneration = this.identityGeneration;
    const scope =
      options.scope ??
      (options.replaceIdentity
        ? 'public'
        : submittedOwner
          ? 'account'
          : 'public');
    const assertOwner = () => {
      if (
        scope === 'account' &&
        (!submittedOwner ||
          submittedOwner !== this.state.session?.user.id ||
          submittedIdentityGeneration !== this.identityGeneration)
      )
        throw new Error(
          'Operação de conta interrompida porque a autenticação mudou.',
        );
    };
    const previousLogout = this.signingOut;
    this.actionPending++;
    const work = async () => {
      await previousLogout;
      if (submittedLogout !== this.logoutGeneration)
        throw new Error('Autenticação interrompida.');
      assertOwner();
      const epoch = ++this.epoch;
      await this.inFlight;
      if (epoch !== this.epoch) throw new Error('Autenticação interrompida.');
      await this.prepareOnlineAction();
      if (epoch !== this.epoch) throw new Error('Autenticação interrompida.');
      assertOwner();
      const result = await action();
      if (epoch !== this.epoch) throw new Error('Autenticação interrompida.');
      if (
        options.invalidateOnUnauthorized &&
        result &&
        typeof result === 'object' &&
        'error' in result &&
        (result.error as { status?: number } | null)?.status === 401
      ) {
        await this.apply(null);
        await this.deps.clearCredentials();
      }
      const effect = options.sessionEffect?.(result) || 'none';
      if (effect === 'challenge') {
        this.challengePending = true;
        await this.apply(null);
      }
      if (effect === 'refresh') {
        if (options.replaceIdentity) await this.apply(null);
        this.challengePending = false;
        await this.performRefresh(epoch, true);
        if (epoch === this.epoch && this.state.session) {
          await this.deps.storage.remove(LOGOUT);
          this.loggedOut = false;
        }
      }
      if (epoch !== this.epoch) throw new Error('Autenticação interrompida.');
      return result;
    };
    const result = this.actionTail.then(work, work);
    this.actionTail = result.then(
      () => {},
      () => {},
    );
    return result.then(
      (value) => {
        this.actionPending--;
        return value;
      },
      (error) => {
        this.actionPending--;
        throw error;
      },
    );
  }
  refresh(): Promise<void> {
    if (this.signingOut) return this.signingOut;
    if (this.actionPending) return this.actionTail;
    if (this.challengePending) return Promise.resolve();
    if (this.inFlight) return this.inFlight;
    this.inFlight = this.performRefresh(this.epoch).finally(() => {
      this.inFlight = null;
    });
    return this.inFlight;
  }
  private async performRefresh(epoch: number, authenticatedAction = false) {
    try {
      if (!(await this.deps.connected())) {
        this.update({ offline: true });
        if (!validSnapshot(this.state.session, this.now()))
          await this.apply(null);
        return;
      }
      if (!(await this.drainQueue())) {
        this.update({ offline: true });
        return;
      }
      if (this.loggedOut && !authenticatedAction) return;
      const result = await this.deps.readSession();
      if (epoch !== this.epoch) return;
      this.update({ offline: result.kind === 'transport' });
      const next = resolveSession(this.state.session, result, this.now());
      await this.apply(next);
      if (result.kind !== 'transport' && !next)
        await this.deps.clearCredentials();
    } catch {
      if (epoch !== this.epoch) return;
      this.update({ offline: true });
      if (!validSnapshot(this.state.session, this.now()))
        await this.apply(null);
    }
  }
  invalidate(): Promise<void> {
    this.epoch++;
    this.logoutGeneration++;
    const cleared = this.apply(null);
    const actions = this.actionTail;
    this.signingOut = (async () => {
      await cleared;
      await this.inFlight;
      await actions;
      await this.deps.clearCredentials();
    })().finally(() => {
      this.signingOut = null;
    });
    return this.signingOut;
  }
  expire() {
    if (!validSnapshot(this.state.session, this.now())) void this.invalidate();
  }
  logout(): Promise<void> {
    if (this.signingOut) return this.signingOut;
    this.epoch++;
    this.logoutGeneration++;
    this.loggedOut = true;
    this.challengePending = false;
    const old = this.state.session;
    const actions = this.actionTail;
    this.deps.resetUserState();
    this.update({ session: null });
    const intent: LogoutIntent = {
      userId: old?.user.id,
      expiresAt: new Date(
        Math.max(
          Date.parse(old?.expiresAt || '') || 0,
          this.now() + SERVER_SESSION_LIFETIME_MS,
        ),
      ).toISOString(),
    };
    const work = async () => {
      // Durable intent comes FIRST. Boot will recover cookies/queue even if killed at the next await.
      await this.deps.storage.set(LOGOUT, JSON.stringify(intent));
      await this.captureRevocation(intent);
      await this.deps.storage.remove(CACHE);
      await this.inFlight;
      await actions;
      // A pending SDK response may have rotated the token; revoke that exact cookie too.
      await this.captureRevocation(intent);
      await this.deps.clearCredentials();
    };
    this.signingOut = work().finally(() => {
      this.signingOut = null;
    });
    return this.signingOut;
  }
}
