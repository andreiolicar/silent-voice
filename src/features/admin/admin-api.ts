export type Session = { user: { email: string }; csrfToken: string }
export class AdminApiError extends Error {
  constructor(public status: number) {
    super(`Request failed (${status})`)
  }
}
export async function adminFetch<T>(
  path: string,
  options: RequestInit = {},
  csrfToken?: string
): Promise<T> {
  const headers = new Headers(options.headers)
  if (options.body) headers.set('Content-Type', 'application/json')
  if (csrfToken) headers.set('X-CSRF-Token', csrfToken)
  const response = await fetch(`/api${path}`, {
    ...options,
    headers,
    credentials: 'same-origin',
  })
  if (!response.ok) throw new AdminApiError(response.status)
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
