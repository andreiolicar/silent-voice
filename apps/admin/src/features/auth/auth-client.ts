import { createAuthClient } from 'better-auth/react'
import { adminClient, twoFactorClient } from 'better-auth/client/plugins'
import { waitForApi } from '@silent-voice/http-client/readiness'

export const authClient = createAuthClient({
  baseURL: window.location.origin,
  basePath: '/api/auth',
  plugins: [adminClient(), twoFactorClient()],
  fetchOptions: { retry: 0, timeout: 20_000 },
})
export type AuthSession = {
  session: { id: string; token: string; expiresAt: string | Date }
  user: {
    id: string
    email: string
    emailVerified: boolean
    role?: string | null
    twoFactorEnabled?: boolean | null
  }
}
type Result<T> = {
  data: T | null
  error: { code?: string; status?: number; message?: string; retryAfterSeconds?: number } | null
}
export class AuthError extends Error {
  constructor(
    public code?: string,
    public status?: number,
    retryAfterSeconds?: number
  ) {
    super(authMessage(code, status, retryAfterSeconds))
  }
}
export function authMessage(code?: string, status?: number, retryAfterSeconds?: number) {
  if (code === 'EMAIL_NOT_VERIFIED')
    return 'Confirme seu e-mail antes de entrar.'
  if (code === 'INVALID_TWO_FACTOR_COOKIE')
    return 'Sua verificação expirou. Volte para entrar novamente.'
  if (status === 429 && typeof retryAfterSeconds === 'number' && Number.isFinite(retryAfterSeconds) && retryAfterSeconds > 0) {
    const minutes = Math.ceil(retryAfterSeconds / 60)
    return `Muitas tentativas. Tente novamente em ${minutes} ${minutes === 1 ? 'minuto' : 'minutos'}.`
  }
  if (status === 429 || code === 'ACCOUNT_TEMPORARILY_LOCKED')
    return 'Muitas tentativas. Aguarde um pouco e tente novamente.'
  if (code?.includes('TOKEN'))
    return 'Este link expirou ou já foi utilizado. Solicite um novo link.'
  if (code?.includes('CODE') || code?.includes('OTP'))
    return 'Código inválido ou expirado. Tente novamente.'
  if (
    code === 'INVALID_EMAIL_OR_PASSWORD' ||
    code === 'INVALID_PASSWORD' ||
    status === 401
  )
    return 'E-mail ou senha incorretos. Tente novamente.'
  if (code?.includes('PASSWORD_TOO'))
    return 'Use uma senha com 12 a 128 caracteres.'
  return 'Não foi possível concluir. Verifique sua conexão e tente novamente.'
}
export async function authResult<T>(operation: Promise<Result<T>>): Promise<T> {
  const result = await operation
  if (result.error) throw new AuthError(result.error.code, result.error.status, result.error.retryAfterSeconds)
  return result.data as T
}
/** Warm only the read-only health route; never replay an uncertain auth POST. */
export async function authAction<T>(
  operation: () => Promise<Result<T>>,
  signal: AbortSignal
): Promise<T> {
  await waitForApi(signal)
  signal.throwIfAborted()
  const result = await authResult(operation())
  signal.throwIfAborted()
  return result
}
export async function getAuthSession(
  signal?: AbortSignal
): Promise<AuthSession | null> {
  const result = await authResult(
    authClient.getSession({
      query: { disableCookieCache: true },
      fetchOptions: { signal },
    })
  )
  if (!result) return null
  const expiresAt = new Date(result.session?.expiresAt ?? '').getTime()
  if (
    !result.user?.id ||
    !result.session?.id ||
    !Number.isFinite(expiresAt) ||
    expiresAt <= Date.now()
  )
    return null
  return result
}
