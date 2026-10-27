import { lazy, Suspense } from 'react'
import { BrowserRouter, useLocation } from 'react-router-dom'
import { LazyMotion, domAnimation } from 'motion/react'
import { LandingPage } from './LandingPage'
import { LoadBoundary } from './components/LoadBoundary'

const AdminApp = lazy(() =>
  import('./features/admin/AdminApp').then((module) => ({
    default: module.AdminApp,
  }))
)

const AccountPages = lazy(() =>
  import('./features/auth/AccountPages').then((module) => ({
    default: module.AccountPages,
  }))
)

function Page() {
  const { pathname, search } = useLocation()
  if (/^\/conta(?:\/|$)/.test(pathname))
    return <AccountPages key={`${pathname}${search}`} />
  return /^\/admin(?:\/|$)/.test(pathname) ? (
    <LoadBoundary
      fallback={
        <p role="alert">
          Não foi possível carregar o painel. Recarregue a página para tentar
          novamente.
        </p>
      }
    >
      <AdminApp />
    </LoadBoundary>
  ) : (
    <LandingPage />
  )
}

export function App() {
  return (
    <LazyMotion features={domAnimation} strict>
      <BrowserRouter>
        <Suspense fallback={<p role="status">Carregando…</p>}>
          <Page />
        </Suspense>
      </BrowserRouter>
    </LazyMotion>
  )
}
