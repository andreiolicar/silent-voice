export type { AuthSession as Session } from '../auth/auth-client'
export class AdminApiError extends Error {
  constructor(
    public status: number,
    public code?: string
  ) {
    super(`Request failed (${status})`)
  }
}
export async function adminFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const headers = new Headers(options.headers)
  if (options.body) headers.set('Content-Type', 'application/json')
  const response = await fetch(`/api${path}`, {
    ...options,
    headers,
    credentials: 'same-origin',
  })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new AdminApiError(response.status, body?.code ?? body?.error)
  }
  return response.status === 204
    ? (undefined as T)
    : (response.json() as Promise<T>)
}
export function isAborted(error: unknown) {
  return error instanceof Error && error.name === 'AbortError'
}
export function apiMessage(error: unknown) {
  if (error instanceof AdminApiError && error.status === 429)
    return 'Muitas tentativas. Aguarde um pouco e tente novamente.'
  if (error instanceof AdminApiError && error.status === 403)
    return 'Não foi possível validar a solicitação. Entre novamente e tente outra vez.'
  return 'Não foi possível concluir. Verifique sua conexão e tente novamente.'
}

export type AdminRequest = <T>(
  path: string,
  options?: RequestInit
) => Promise<T>
