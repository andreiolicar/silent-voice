import * as SecureStore from 'expo-secure-store';
export const storage = {
  get: SecureStore.getItemAsync,
  set: SecureStore.setItemAsync,
  remove: SecureStore.deleteItemAsync,
};
export const persistentIdentity = true;
