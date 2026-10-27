import { useEffect, useRef, useState } from 'react'
import { AuthError } from './auth-client'

export function useAuthTask(onSessionExpired?: () => void) {
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')
  const controller = useRef<AbortController | null>(null)
  const errorRef = useRef<HTMLParagraphElement>(null)
  useEffect(() => () => controller.current?.abort(), [])
  useEffect(() => {
    if (error) errorRef.current?.focus()
  }, [error])
  async function run(operation: (signal: AbortSignal) => Promise<void>) {
    if (controller.current && !controller.current.signal.aborted) return
    const active = new AbortController()
    controller.current = active
    setPending(true)
    setError('')
    try {
      await operation(active.signal)
    } catch (cause) {
      if (
        !active.signal.aborted &&
        cause instanceof AuthError &&
        ['UNAUTHORIZED', 'SESSION_EXPIRED', 'SESSION_NOT_FRESH'].includes(
          cause.code ?? ''
        ) &&
        onSessionExpired
      ) {
        onSessionExpired()
        return
      }
      if (!active.signal.aborted)
        setError(
          cause instanceof AuthError
            ? cause.message
            : 'Não foi possível concluir. Verifique sua conexão e tente novamente.'
        )
    } finally {
      if (!active.signal.aborted) setPending(false)
      if (controller.current === active) controller.current = null
    }
  }
  return { pending, error, setError, errorRef, run }
}
