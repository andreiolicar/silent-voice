import { createAuthClient } from 'better-auth/react';
import { twoFactorClient } from 'better-auth/client/plugins';
import { expoClient, storageAdapter } from '@better-auth/expo/client';
import * as SecureStore from 'expo-secure-store';

export const AUTH_URL =
  process.env.EXPO_PUBLIC_AUTH_URL || 'https://www.silentvoice.com.br';
export const authClient = createAuthClient({
  baseURL: AUTH_URL,
  basePath: '/api/auth',
  plugins: [
    twoFactorClient(),
    expoClient({
      scheme: 'silentvoicemobile',
      storagePrefix: 'sv.auth',
      storage: SecureStore,
      disableCache: true,
    }),
  ],
  fetchOptions: { retry: 0, timeout: 15000 },
});
export async function getNativeCookie(): Promise<string> {
  const cookies = (await authClient.getCookie()) || '';
  return cookies
    .split(';')
    .map((item) => item.trim())
    .filter((item) => /^(?:__Secure-)?better-auth\.session_token=/.test(item))
    .join('; ');
}
export async function clearNativeCredentials(): Promise<void> {
  await storageAdapter(SecureStore).setItemAsync('sv.auth_cookie', '{}');
  await storageAdapter(SecureStore).setItemAsync('sv.auth_session_data', '{}');
}
