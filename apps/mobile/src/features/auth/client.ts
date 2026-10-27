import { createAuthClient } from 'better-auth/react';
import { twoFactorClient } from 'better-auth/client/plugins';

export const AUTH_URL =
  process.env.EXPO_PUBLIC_AUTH_URL || 'https://www.silentvoice.com.br';
export const authClient = createAuthClient({
  baseURL: AUTH_URL,
  basePath: '/api/auth',
  plugins: [twoFactorClient()],
  fetchOptions: { retry: 0, timeout: 15000 },
});
export async function getNativeCookie(): Promise<string> {
  return '';
}
export async function clearNativeCredentials(): Promise<void> {}
