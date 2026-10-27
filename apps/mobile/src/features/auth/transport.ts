import { createAuthClient } from 'better-auth/react';
import { AUTH_URL, authClient } from './client';
import type { SessionResult } from '@/domain/auth/policy';

export async function readSession(): Promise<SessionResult> {
  try {
    const result = await authClient.getSession({
      query: { disableCookieCache: true },
      fetchOptions: { retry: 0, timeout: 15000 },
    });
    if (result.error)
      return {
        kind:
          result.error.status === 401 || result.error.status === 403
            ? 'invalid'
            : 'transport',
      };
    const s = result.data;
    return {
      kind: 'valid',
      snapshot: s
        ? {
            user: {
              id: s.user.id,
              name: s.user.name,
              email: s.user.email,
              emailVerified: s.user.emailVerified,
              twoFactorEnabled: Boolean(s.user.twoFactorEnabled),
            },
            expiresAt: new Date(s.session.expiresAt).toISOString(),
          }
        : null,
    };
  } catch {
    return { kind: 'transport' };
  }
}
/** Separate client has no cookie storage or current user context. */
export async function revokeCapturedSession(cookie: string): Promise<boolean> {
  const isolated = createAuthClient({
    baseURL: AUTH_URL,
    basePath: '/api/auth',
    fetchOptions: {
      credentials: 'omit',
      headers: {
        Cookie: cookie,
        'expo-origin': 'silentvoicemobile://',
        'x-skip-oauth-proxy': 'true',
      },
      retry: 0,
      timeout: 15000,
    },
  });
  const result = await isolated.signOut();
  return !result.error || result.error.status === 401;
}
