import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type PropsWithChildren,
} from 'react';
import { AppState, Platform } from 'react-native';
import * as Network from 'expo-network';
import {
  SessionCoordinator,
  type AuthState,
  type AuthActionOptions,
} from '@/domain/auth/coordinator';
import { useDeviceStore } from '@/stores/device.store';
import { authClient, clearNativeCredentials, getNativeCookie } from './client';
import { persistentIdentity, storage } from './storage';
import { readSession, revokeCapturedSession } from './transport';

type AuthContextValue = AuthState & {
  runAuthAction: <T>(
    action: () => Promise<T>,
    options?: AuthActionOptions<T>,
  ) => Promise<T>;
  refresh: () => Promise<void>;
  prepareOnlineAction: () => Promise<void>;
  invalidate: () => Promise<void>;
  finishOnboarding: () => Promise<void>;
  logout: () => Promise<void>;
};
const AuthContext = createContext<AuthContextValue | null>(null);
async function connected() {
  const network = await Network.getNetworkStateAsync();
  return network.isConnected !== false && network.isInternetReachable !== false;
}
export function AuthProvider({ children }: PropsWithChildren) {
  const [state, setState] = useState<AuthState>({
    ready: false,
    onboarding: false,
    session: null,
    offline: false,
  });
  const [coordinator] = useState(
    () =>
      new SessionCoordinator({
        persistentIdentity,
        storage,
        connected,
        readSession,
        cookie: getNativeCookie,
        clearCredentials: clearNativeCredentials,
        revoke: async (cookie, userId) => {
          if (Platform.OS === 'web') {
            const current = await authClient.getSession({
              query: { disableCookieCache: true },
            });
            if (current.error) return current.error.status === 401;
            if (!current.data || current.data.user.id !== userId) return true;
            const result = await authClient.revokeSession({
              token: current.data.session.token,
            });
            return !result.error || result.error.status === 401;
          }
          return revokeCapturedSession(cookie);
        },
        resetUserState: () =>
          useDeviceStore.getState().setConnectionState('disconnected'),
        onChange: setState,
      }),
  );
  useEffect(() => {
    void coordinator.boot();
    const network = Network.addNetworkStateListener((value) => {
      if (value.isConnected) void coordinator.refresh();
    });
    const app = AppState.addEventListener('change', (value) => {
      if (value === 'active') void coordinator.refresh();
    });
    return () => {
      network.remove();
      app.remove();
    };
  }, [coordinator]);
  useEffect(() => {
    if (!state.session) return;
    const timeout = setTimeout(
      () => coordinator.expire(),
      Math.min(
        2147483647,
        Math.max(0, Date.parse(state.session.expiresAt) - Date.now()),
      ),
    );
    return () => clearTimeout(timeout);
  }, [coordinator, state.session]);
  const runAuthAction = useCallback(
    <T,>(action: () => Promise<T>, options?: AuthActionOptions<T>) =>
      coordinator.runAuthAction(action, options),
    [coordinator],
  );
  const refresh = useCallback(() => coordinator.refresh(), [coordinator]);
  const prepareOnlineAction = useCallback(
    () => coordinator.prepareOnlineAction(),
    [coordinator],
  );
  const invalidate = useCallback(() => coordinator.invalidate(), [coordinator]);
  const finishOnboarding = useCallback(
    () => coordinator.finishOnboarding(),
    [coordinator],
  );
  const logout = useCallback(async () => {
    await coordinator.logout();
    if (await connected()) await coordinator.drainQueue();
  }, [coordinator]);
  return (
    <AuthContext.Provider
      value={{
        ...state,
        runAuthAction,
        refresh,
        prepareOnlineAction,
        invalidate,
        finishOnboarding,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error('AuthProvider required');
  return value;
}
