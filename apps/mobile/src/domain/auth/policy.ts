/** Local identity grants offline UI access only, never API authorization. */
export type SessionSnapshot = {
  user: {
    id: string;
    name: string;
    email: string;
    emailVerified: boolean;
    twoFactorEnabled?: boolean;
  };
  expiresAt: string;
};
export type SessionResult =
  | { kind: 'valid'; snapshot: SessionSnapshot | null }
  | { kind: 'invalid' }
  | { kind: 'transport' };
export type PendingRevocation = {
  cookie: string;
  expiresAt: string;
  userId?: string;
};
export function validSnapshot(
  value: unknown,
  now = Date.now(),
): value is SessionSnapshot {
  if (!value || typeof value !== 'object') return false;
  const s = value as SessionSnapshot;
  return Boolean(
    s.user?.id &&
    s.user?.email &&
    s.user?.emailVerified === true &&
    Number.isFinite(Date.parse(s.expiresAt)) &&
    Date.parse(s.expiresAt) > now,
  );
}
export function resolveSession(
  cached: SessionSnapshot | null,
  result: SessionResult,
  now = Date.now(),
): SessionSnapshot | null {
  const next =
    result.kind === 'transport'
      ? cached
      : result.kind === 'valid'
        ? result.snapshot
        : null;
  return validSnapshot(next, now) ? next : null;
}
export function validateCredentials(
  email: string,
  password: string,
  confirmation?: string,
): string | null {
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim()))
    return 'Informe um e-mail válido.';
  if (password.length < 12 || password.length > 128)
    return 'Use uma senha com 12 a 128 caracteres.';
  if (confirmation !== undefined && confirmation !== password)
    return 'As senhas precisam ser iguais.';
  return null;
}
export async function flushRevocations(
  pending: PendingRevocation[],
  revoke: (cookie: string, userId?: string) => Promise<boolean>,
  now = Date.now(),
): Promise<PendingRevocation[]> {
  const remaining: PendingRevocation[] = [];
  for (const item of pending) {
    if (Date.parse(item.expiresAt) <= now) continue;
    try {
      if (!(await revoke(item.cookie, item.userId))) remaining.push(item);
    } catch {
      remaining.push(item);
    }
  }
  return remaining;
}
