import './admin.css'
import { useCallback, useEffect, useRef, useState } from 'react'
import {
  Navigate,
  Outlet,
  Route,
  Routes,
  useLocation,
  useNavigate,
} from 'react-router-dom'
import { AdminApiError, adminFetch, apiMessage, isAborted } from './admin-api'
import type { Session, AdminRequest as Request } from './admin-api'
import type { LeadDraft } from './LeadPanel'
import { Login } from './Login'
import { AdminLayout } from './AdminLayout'
import { Overview } from './Overview'
import { ContactsPage } from './ContactsPage'
import { AdminButton } from './AdminButton'

export function AdminApp() {
  const navigate = useNavigate()
  const location = useLocation()
  const [session, setSession] = useState<Session | null>(null)
  const [checking, setChecking] = useState(true)
  const [sessionError, setSessionError] = useState('')
  const [sessionRetry, setSessionRetry] = useState(0)
  const [expired, setExpired] = useState(false)
  const [drafts, setDrafts] = useState<Record<string, LeadDraft>>({})
  const [loggingOut, setLoggingOut] = useState(false)
  const [logoutError, setLogoutError] = useState('')
  const logoutController = useRef<AbortController | null>(null)
  useEffect(() => () => logoutController.current?.abort(), [])
  const login = location.pathname === '/admin/login'
  const expire = useCallback(() => {
    setSession(null)
    setExpired(true)
    navigate('/admin/login', { replace: true })
  }, [navigate])
  useEffect(() => {
    if (login || session) {
      setChecking(false)
      return
    }
    const controller = new AbortController()
    setChecking(true)
    setSessionError('')
    adminFetch<Session>('/auth/session', { signal: controller.signal })
      .then(setSession)
      .catch((error) => {
        if (isAborted(error)) return
        if (error instanceof AdminApiError && error.status === 401) expire()
        else setSessionError(apiMessage(error))
      })
      .finally(() => {
        if (!controller.signal.aborted) setChecking(false)
      })
    return () => controller.abort()
  }, [login, session, sessionRetry, expire])
  const request: Request = useCallback(
    async <T,>(path: string, options?: RequestInit) => {
      try {
        return await adminFetch<T>(path, options, session?.csrfToken)
      } catch (error) {
        if (error instanceof AdminApiError && error.status === 401) expire()
        throw error
      }
    },
    [session?.csrfToken, expire]
  )
  const updateDraft = useCallback((id: string, update: Partial<LeadDraft>) => {
    setDrafts((previous) => ({
      ...previous,
      [id]: { ...(previous[id] ?? { text: '' }), ...update },
    }))
  }, [])
  async function logout() {
    if (loggingOut) return
    const controller = new AbortController()
    logoutController.current = controller
    setLoggingOut(true)
    setLogoutError('')
    try {
      await request('/auth/logout', { method: 'POST', signal: controller.signal })
      if (controller.signal.aborted) return
      setSession(null)
      setDrafts({})
      setExpired(false)
      navigate('/admin/login', { replace: true })
    } catch (error) {
      if (!controller.signal.aborted && !isAborted(error)) setLogoutError(apiMessage(error))
    } finally {
      if (!controller.signal.aborted) setLoggingOut(false)
    }
  }

  const protectedContent = checking ? (
    <div className="admin-boot" role="status">Carregando área de gestão…</div>
  ) : sessionError ? (
    <div className="admin-boot">
      <p role="alert">{sessionError}</p>
      <AdminButton onClick={() => setSessionRetry((value) => value + 1)}>
        Tentar novamente
      </AdminButton>
    </div>
  ) : session ? (
    <AdminLayout
      email={session.user.email}
      onLogout={logout}
      loggingOut={loggingOut}
      logoutError={logoutError}
    >
      <Outlet />
    </AdminLayout>
  ) : <Navigate to="/admin/login" replace />

  return (
    <div className="admin-shell">
      <Routes>
        <Route
          path="/admin/login"
          element={
            <Login
              expired={expired}
              onLogin={(value) => {
                setSession(value)
                setExpired(false)
                setLogoutError('')
                navigate('/admin', { replace: true })
              }}
            />
          }
        />
        <Route path="/admin" element={protectedContent}>
          <Route index element={<Overview request={request} />} />
          <Route path="cadastros" element={
            <ContactsPage key="register" request={request} drafts={drafts} updateDraft={updateDraft} />
          } />
          <Route path="acompanhamento" element={
            <ContactsPage key="tracking" view="tracking" request={request} drafts={drafts} updateDraft={updateDraft} />
          } />
          <Route path="*" element={<Navigate to="/admin" replace />} />
        </Route>
        <Route path="*" element={<Navigate to="/admin" replace />} />
      </Routes>
    </div>
  )
}
