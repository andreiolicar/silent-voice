/** Normal product destination when leaving the private lab. */
export function labReturnDestination(
  hasSession: boolean,
  onboarding: boolean,
): '/(main)/home' | '/auth/login' | '/onboarding' {
  return hasSession
    ? '/(main)/home'
    : onboarding
      ? '/auth/login'
      : '/onboarding';
}
