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
import { authAction, authClient, getAuthSession } from '../auth/auth-client'
import { SecurityPage } from '../auth/SecurityPage'

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
  const [securityLocked, setSecurityLocked] = useState(false)
  const [forbidden, setForbidden] = useState(false)
  const logoutController = useRef<AbortController | null>(null)
  const identity = useRef<string | null>(null)
  const epoch = useRef(0)
  useEffect(() => () => logoutController.current?.abort(), [])
  const login = location.pathname === '/admin/login'
  const expire = useCallback(() => {
    epoch.current += 1
    setSession(null)
    setExpired(identity.current !== null)
    setForbidden(false)
    navigate('/admin/login', { replace: true })
  }, [navigate])
  const acceptSession = useCallback((value: Session) => {
    epoch.current += 1
    if (identity.current !== value.user.id) setDrafts({})
    identity.current = value.user.id
    setSecurityLocked(false)
    setSession(value)
    setSessionError('')
    setForbidden(false)
    setExpired(false)
    setLogoutError('')
  }, [])
  useEffect(() => {
    if (login || session) {
      setChecking(false)
      return
    }
    const controller = new AbortController()
    const generation = epoch.current
    setChecking(true)
    setSessionError('')
    getAuthSession(controller.signal)
      .then((value) => {
        if (controller.signal.aborted || generation !== epoch.current) return
        if (value) acceptSession(value)
        else expire()
      })
      .catch((error) => {
        if (
          controller.signal.aborted ||
          generation !== epoch.current ||
          isAborted(error)
        )
          return
        if (error?.status === 401) expire()
        else setSessionError(apiMessage(error))
      })
      .finally(() => {
        if (!controller.signal.aborted) setChecking(false)
      })
    return () => controller.abort()
  }, [login, session, sessionRetry, expire, acceptSession])
  useEffect(() => {
    if (!session) return
    const remaining = new Date(session.session.expiresAt).getTime() - Date.now()
    const timer = setTimeout(
      expire,
      Math.max(0, Math.min(remaining, 2_147_483_647))
    )
    return () => clearTimeout(timer)
  }, [session, expire])
  const request: Request = useCallback(
    async <T,>(path: string, options?: RequestInit) => {
      const generation = epoch.current
      try {
        return await adminFetch<T>(path, options)
      } catch (error) {
        if (generation === epoch.current && error instanceof AdminApiError) {
          if (error.status === 401) expire()
          else if (
            error.status === 403 &&
            error.code === 'MFA_SETUP_REQUIRED'
          ) {
            setSession((value) =>
              value
                ? { ...value, user: { ...value.user, twoFactorEnabled: false } }
                : null
            )
            navigate('/admin/seguranca', { replace: true })
          } else if (error.status === 403) setForbidden(true)
        }
        throw error
      }
    },
    [expire, navigate]
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
      await authAction(
        () =>
          authClient.signOut({ fetchOptions: { signal: controller.signal } }),
        controller.signal
      )
      epoch.current += 1
      identity.current = null
      setSession(null)
      setDrafts({})
      setExpired(false)
      setForbidden(false)
      navigate('/admin/login', { replace: true })
    } catch (error) {
      if (!controller.signal.aborted && !isAborted(error))
        setLogoutError(apiMessage(error))
    } finally {
      if (!controller.signal.aborted) setLoggingOut(false)
    }
  }
  const security = session ? (
    <SecurityPage
      key={session.user.id}
      session={session}
      onLogout={logout}
      onReauthenticate={expire}
      onSessionRevoked={() => setSecurityLocked(true)}
      onSessionChanged={acceptSession}
    />
  ) : null
  const denied =
    session &&
    (forbidden || session.user.role !== 'admin' || !session.user.emailVerified)
  const protectedContent = checking ? (
    <div className="admin-boot" role="status">
      Carregando área de gestão…
    </div>
  ) : sessionError ? (
    <div className="admin-boot">
      <p role="alert">{sessionError}</p>
      <AdminButton onClick={() => setSessionRetry((value) => value + 1)}>
        Tentar novamente
      </AdminButton>
    </div>
  ) : denied ? (
    <div className="admin-boot">
      <h1>Acesso restrito</h1>
      <p>Esta área exige uma conta administrativa com e-mail confirmado.</p>
      {logoutError && <p role="alert">{logoutError}</p>}
      <AdminButton onClick={logout} disabled={loggingOut}>
        Sair
      </AdminButton>
    </div>
  ) : session ? (
    <AdminLayout
      key={session.user.id}
      email={session.user.email}
      onLogout={logout}
      loggingOut={loggingOut}
      logoutError={logoutError}
      securityOnly={!session.user.twoFactorEnabled || securityLocked}
    >
      {(!session.user.twoFactorEnabled || securityLocked) &&
      location.pathname !== '/admin/seguranca' ? (
        <Navigate to="/admin/seguranca" replace />
      ) : (
        <Outlet />
      )}
    </AdminLayout>
  ) : (
    <Navigate to="/admin/login" replace />
  )
  return (
    <div className="admin-shell">
      <Routes>
        <Route
          path="/admin/login"
          element={
            <Login
              expired={expired}
              onLogin={(value) => {
                acceptSession(value)
                navigate(
                  value.user.twoFactorEnabled ? '/admin' : '/admin/seguranca',
                  { replace: true }
                )
              }}
            />
          }
        />
        <Route path="/admin" element={protectedContent}>
          <Route index element={<Overview request={request} />} />
          <Route path="seguranca" element={security} />
          <Route
            path="cadastros"
            element={
              <ContactsPage
                key="register"
                request={request}
                drafts={drafts}
                updateDraft={updateDraft}
              />
            }
          />
          <Route
            path="acompanhamento"
            element={
              <ContactsPage
                key="tracking"
                view="tracking"
                request={request}
                drafts={drafts}
                updateDraft={updateDraft}
              />
            }
          />
          <Route path="*" element={<Navigate to="/admin" replace />} />
        </Route>
        <Route path="*" element={<Navigate to="/admin" replace />} />
      </Routes>
    </div>
  )
}
